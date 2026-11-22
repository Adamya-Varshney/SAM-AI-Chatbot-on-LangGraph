-- SAM AI Chatbot v2 — Database Migration
-- Run this in Supabase SQL Editor (Dashboard > SQL Editor > New Query)

-- 1. Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. Create tables

-- 2.1 Thread metadata
CREATE TABLE public.thread_metadata (
    thread_id   TEXT        PRIMARY KEY,
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title       TEXT        NOT NULL DEFAULT 'New Chat',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_thread_metadata_user ON public.thread_metadata(user_id);
CREATE INDEX idx_thread_metadata_user_created ON public.thread_metadata(user_id, created_at DESC);

-- 2.2 User long-term memories
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

-- 2.3 Document chunks (PDF RAG)
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

-- 2.4 Document metadata
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

-- 2.5 OAuth tokens for MCP integrations
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

-- 3. Enable RLS on all tables

ALTER TABLE public.thread_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_oauth_tokens ENABLE ROW LEVEL SECURITY;

-- 4. RLS policies — thread_metadata

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

-- 5. RLS policies — user_memories

CREATE POLICY "Users can view own memories"
    ON public.user_memories FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own memories"
    ON public.user_memories FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own memories"
    ON public.user_memories FOR DELETE
    USING (auth.uid() = user_id);

-- 6. RLS policies — document_chunks

CREATE POLICY "Users can view own documents"
    ON public.document_chunks FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own documents"
    ON public.document_chunks FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own documents"
    ON public.document_chunks FOR DELETE
    USING (auth.uid() = user_id);

-- 7. RLS policies — document_metadata

CREATE POLICY "Users can view own document metadata"
    ON public.document_metadata FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own document metadata"
    ON public.document_metadata FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own document metadata"
    ON public.document_metadata FOR DELETE
    USING (auth.uid() = user_id);

-- 8. RLS policies — user_oauth_tokens

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

-- 9. Auto-update updated_at trigger

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.thread_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.user_memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER set_updated_at BEFORE UPDATE ON public.user_oauth_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
