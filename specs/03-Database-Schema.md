# SAM AI Chatbot v2 — Database Schema Spec

**Version:** 1.0
**Date:** 2026-11-21
**Parent:** [01-PRD.md](./01-PRD.md)

---

## 1. Overview

All data lives in a single Supabase PostgreSQL instance (Pro plan, 8GB). The database uses:
- **Supabase Auth** (`auth` schema) — managed user accounts
- **pgvector** extension — vector similarity search for RAG and long-term memory
- **Row Level Security (RLS)** — enforced on all user-scoped tables
- **langgraph-checkpoint-postgres** — managed checkpoint tables (internal schema)

---

## 2. Extensions

```sql
-- Enable pgvector for embedding storage and similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable crypto functions for token encryption
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

---

## 3. Tables

### 3.1 thread_metadata

Stores conversation metadata. One row per chat thread.

```sql
CREATE TABLE public.thread_metadata (
    thread_id   TEXT        PRIMARY KEY,
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title       TEXT        NOT NULL DEFAULT 'New Chat',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_thread_metadata_user ON public.thread_metadata(user_id);
CREATE INDEX idx_thread_metadata_user_created ON public.thread_metadata(user_id, created_at DESC);
```

**RLS Policies:**
```sql
ALTER TABLE public.thread_metadata ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own threads"
    ON public.thread_metadata FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own threads"
    ON public.thread_metadata FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own threads"
    ON public.thread_metadata FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own threads"
    ON public.thread_metadata FOR DELETE
    USING (auth.uid() = user_id);
```

**Migration from v1:** The existing `thread_metadata` table in SQLite has `thread_id`, `title`, `created_at` but no `user_id`. Since v1 has no auth, all existing threads are unowned. Migration strategy: assign all existing threads to a designated "legacy" user or discard them (data was ephemeral on Streamlit Cloud anyway).

---

### 3.2 user_memories

Long-term facts about a user, stored with embeddings for semantic recall.

```sql
CREATE TABLE public.user_memories (
    id          UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID            NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content     TEXT            NOT NULL,
    category    TEXT            NOT NULL DEFAULT 'general',
    embedding   vector(1536)    NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_memories_user ON public.user_memories(user_id);
CREATE INDEX idx_user_memories_category ON public.user_memories(user_id, category);
CREATE INDEX idx_user_memories_embedding ON public.user_memories
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**Categories:**
| Category | Example content |
|----------|----------------|
| `general` | "User's name is Adamya" |
| `preference` | "User prefers dark mode" |
| `project` | "User is building a chatbot with LangGraph" |
| `technical` | "User works with Python and Next.js" |
| `personal` | "User is based in Noida, India" |

**RLS Policies:**
```sql
ALTER TABLE public.user_memories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own memories"
    ON public.user_memories FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own memories"
    ON public.user_memories FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own memories"
    ON public.user_memories FOR DELETE
    USING (auth.uid() = user_id);
```

---

### 3.3 document_chunks

PDF text chunks with vector embeddings for RAG retrieval. Replaces the in-memory FAISS store from v1.

```sql
CREATE TABLE public.document_chunks (
    id              UUID            PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID            NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    thread_id       TEXT            NOT NULL,
    filename        TEXT            NOT NULL,
    page_number     INTEGER,
    chunk_index     INTEGER         NOT NULL,
    content         TEXT            NOT NULL,
    embedding       vector(1536)    NOT NULL,
    metadata        JSONB           DEFAULT '{}',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX idx_document_chunks_user ON public.document_chunks(user_id);
CREATE INDEX idx_document_chunks_thread ON public.document_chunks(user_id, thread_id);
CREATE INDEX idx_document_chunks_embedding ON public.document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**RLS Policies:**
```sql
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own documents"
    ON public.document_chunks FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own documents"
    ON public.document_chunks FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own documents"
    ON public.document_chunks FOR DELETE
    USING (auth.uid() = user_id);
```

**RAG query pattern:**
```sql
-- Find top 4 most similar chunks for a user's thread
SELECT content, metadata, filename, page_number,
       1 - (embedding <=> $1::vector) AS similarity
FROM public.document_chunks
WHERE user_id = $2 AND thread_id = $3
ORDER BY embedding <=> $1::vector
LIMIT 4;
```

---

### 3.4 document_metadata

Summary info per uploaded document (for UI display). One row per PDF per thread.

```sql
CREATE TABLE public.document_metadata (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    thread_id   TEXT        NOT NULL,
    filename    TEXT        NOT NULL,
    page_count  INTEGER     NOT NULL,
    chunk_count INTEGER     NOT NULL,
    file_size   INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, thread_id, filename)
);

CREATE INDEX idx_document_metadata_thread ON public.document_metadata(user_id, thread_id);
```

**RLS Policies:**
```sql
ALTER TABLE public.document_metadata ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own document metadata"
    ON public.document_metadata FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own document metadata"
    ON public.document_metadata FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own document metadata"
    ON public.document_metadata FOR DELETE
    USING (auth.uid() = user_id);
```

---

### 3.5 user_oauth_tokens

Encrypted OAuth tokens for MCP integrations (Google Drive, GitHub).

```sql
CREATE TABLE public.user_oauth_tokens (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider        TEXT        NOT NULL,
    access_token    TEXT        NOT NULL,
    refresh_token   TEXT,
    token_expiry    TIMESTAMPTZ,
    scopes          TEXT[]      DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, provider)
);

CREATE INDEX idx_oauth_tokens_user ON public.user_oauth_tokens(user_id);
```

**Encryption:** `access_token` and `refresh_token` values are encrypted using AES-256-GCM before insertion. The encryption key is the `ENCRYPTION_KEY` environment variable on Railway, never stored in the database. The backend encrypts on write and decrypts on read.

**Providers:**
| Provider | Scopes | Token refresh? |
|----------|--------|---------------|
| `google` | `drive.readonly` (expandable) | Yes — refresh_token used to get new access_token |
| `github` | `repo`, `read:user` | No — GitHub tokens don't expire (unless revoked) |

**RLS Policies:**
```sql
ALTER TABLE public.user_oauth_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own tokens"
    ON public.user_oauth_tokens FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own tokens"
    ON public.user_oauth_tokens FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own tokens"
    ON public.user_oauth_tokens FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own tokens"
    ON public.user_oauth_tokens FOR DELETE
    USING (auth.uid() = user_id);
```

---

### 3.6 LangGraph Checkpoint Tables

Managed by `langgraph-checkpoint-postgres`. The library creates its own tables when `checkpointer.setup()` is called:

- `checkpoints` — serialized graph state per (thread_id, checkpoint_id)
- `checkpoint_writes` — pending writes
- `checkpoint_migrations` — schema version tracking

These tables do NOT have RLS by default. The backend accesses them using a service role connection (bypasses RLS) and enforces user isolation at the application layer by only querying checkpoints for thread_ids that belong to the authenticated user (verified via `thread_metadata`).

---

## 4. Entity Relationship Diagram

```
auth.users (Supabase managed)
    |
    |-- 1:N --> thread_metadata (user_id)
    |               |
    |               |-- thread_id referenced by:
    |               |       document_chunks (thread_id)
    |               |       document_metadata (thread_id)
    |               |       LangGraph checkpoints (thread_id)
    |
    |-- 1:N --> user_memories (user_id)
    |
    |-- 1:N --> document_chunks (user_id)
    |
    |-- 1:N --> document_metadata (user_id)
    |
    |-- 1:N --> user_oauth_tokens (user_id)
         (max 1 per provider via UNIQUE constraint)
```

---

## 5. Database Access Patterns

### 5.1 Backend Connection

The backend uses TWO connection patterns:

1. **Service role connection** (bypasses RLS) — for LangGraph checkpoints and operations that span users (admin-like)
   ```
   SUPABASE_DB_URL=postgresql://postgres:<service-role-password>@db.<ref>.supabase.co:5432/postgres
   ```

2. **User-scoped queries** — backend manually adds `WHERE user_id = $user_id` to all queries on user-scoped tables. RLS is an additional safety net.

### 5.2 Query Patterns by Endpoint

| Endpoint | Tables touched | Query type |
|----------|---------------|------------|
| `POST /api/chat` | thread_metadata, user_memories, document_chunks, checkpoints | SELECT (memories, vectors), INSERT (checkpoint) |
| `GET /api/threads` | thread_metadata | SELECT with user_id filter |
| `PATCH /api/threads/{id}` | thread_metadata | UPDATE title |
| `DELETE /api/threads/{id}` | thread_metadata, document_chunks, document_metadata, checkpoints | CASCADE DELETE |
| `POST /api/documents/upload` | document_chunks, document_metadata | INSERT (bulk chunks + metadata) |
| `GET /api/memories` | user_memories | SELECT with user_id filter |
| `DELETE /api/memories/{id}` | user_memories | DELETE by id + user_id |
| `GET /api/auth/connections` | user_oauth_tokens | SELECT providers for user |

---

## 6. Migration SQL

Complete migration script to run on a fresh Supabase project:

```sql
-- 1. Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. Create tables
-- (see individual CREATE TABLE statements in sections 3.1-3.5 above)

-- 3. Enable RLS on all tables
-- (see individual ALTER TABLE + CREATE POLICY statements above)

-- 4. Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5. Apply updated_at triggers
CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.thread_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.user_memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.user_oauth_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 6. LangGraph checkpoint tables are created by the library at startup
-- (checkpointer.setup() handles this)
```

---

## 7. Storage Estimates

| Table | Row size (est.) | Rows per active user | Storage per user |
|-------|----------------|---------------------|-----------------|
| thread_metadata | ~200 bytes | ~50 threads | ~10 KB |
| user_memories | ~6.5 KB (1536 floats + text) | ~100 memories | ~650 KB |
| document_chunks | ~6.5 KB (1536 floats + text) | ~500 chunks (5 PDFs) | ~3.25 MB |
| document_metadata | ~200 bytes | ~5 docs | ~1 KB |
| user_oauth_tokens | ~500 bytes | ~2 providers | ~1 KB |
| checkpoints | ~5 KB per checkpoint | ~200 checkpoints | ~1 MB |

**Per active user: ~5 MB**
**Supabase Pro limit: 8 GB**
**Capacity: ~1,600 active users** before needing to manage storage

---

## 8. Indexing Strategy

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| thread_metadata | `(user_id)` | B-tree | Filter threads by user |
| thread_metadata | `(user_id, created_at DESC)` | B-tree | Sorted thread listing |
| user_memories | `(user_id)` | B-tree | Filter memories by user |
| user_memories | `(embedding)` | IVFFlat (cosine) | Semantic similarity search |
| document_chunks | `(user_id, thread_id)` | B-tree | Filter chunks by user+thread |
| document_chunks | `(embedding)` | IVFFlat (cosine) | RAG vector search |
| document_metadata | `(user_id, thread_id)` | B-tree | List docs per thread |
| user_oauth_tokens | `(user_id)` | B-tree | Lookup user's connections |

IVFFlat indexes use `lists = 100` initially. If a table grows past 100K rows, rebuild with `lists = sqrt(row_count)`.
