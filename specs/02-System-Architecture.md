# SAM AI Chatbot v2 — System Architecture Spec

**Version:** 1.0
**Date:** 2026-11-21
**Parent:** [01-PRD.md](./01-PRD.md)

---

## 1. Service Topology

Three independently deployed services, one managed database:

```
                        Internet
                           |
              ┌────────────┴────────────┐
              v                         v
     ┌────────────────┐       ┌─────────────────┐
     │  Next.js App   │       │  FastAPI Server  │
     │  (Vercel)      │       │  (Railway)       │
     │                │       │                  │
     │  Static + SSR  │──────>│  REST + SSE      │
     │  React SPA     │ HTTPS │  LangGraph Agent │
     │  Vercel AI SDK │       │  MCP Client      │
     └────────────────┘       └───────┬──────────┘
                                      │
                              ┌───────┴──────────┐
                              v                  v
                     ┌──────────────┐   ┌──────────────┐
                     │  Supabase    │   │  MCP Servers  │
                     │  PostgreSQL  │   │  (Remote)     │
                     │  + pgvector  │   │               │
                     │  + Auth      │   │  Google Drive │
                     │  + RLS       │   │  GitHub       │
                     └──────────────┘   └──────────────┘
```

| Service | Host | URL pattern | Always on? |
|---------|------|-------------|-----------|
| Frontend | Vercel | `sam-ai.vercel.app` (or custom domain) | Yes (CDN + serverless) |
| Backend | Railway | `sam-api-production.up.railway.app` | Yes (persistent process) |
| Database | Supabase | `<project-ref>.supabase.co` | Yes (managed) |
| Google Drive MCP | Zomato-hosted pattern | Remote HTTP | On demand |
| GitHub MCP | Community / self-run | stdio via mcp-remote | On demand |

---

## 2. Service Responsibilities

### 2.1 Frontend (Next.js on Vercel)

**Responsibilities:**
- Render chat UI (message list, input bar, sidebar)
- Handle user authentication flows (login, signup, OAuth redirects)
- Stream AI responses via SSE using Vercel AI SDK `useChat()`
- Manage client-side state (current thread, theme, sidebar open/closed)
- File upload (PDF) with progress indication
- Display connected integrations status

**Does NOT:**
- Call OpenAI directly
- Access the database directly
- Run LangGraph or any agent logic
- Store sensitive data (tokens, keys)

### 2.2 Backend (FastAPI on Railway)

**Responsibilities:**
- Expose REST API for all operations (chat, threads, documents, auth, memory)
- Run LangGraph agent (chat_node <-> tools loop)
- Stream AI responses via SSE (`text/event-stream`)
- Validate JWTs from Supabase Auth on every request
- Manage MCP client connections (Google Drive, GitHub)
- Load user-specific tools based on connected OAuth providers
- Ingest PDFs: chunk, embed, store vectors in pgvector
- Manage long-term user memory (store, recall, forget)
- Refresh expired OAuth tokens automatically

**Does NOT:**
- Serve static assets (that's Vercel's job)
- Handle user registration directly (that's Supabase Auth)
- Store files permanently (PDFs are processed and discarded; vectors go to pgvector)

### 2.3 Database (Supabase PostgreSQL)

**Responsibilities:**
- User accounts and sessions (Supabase Auth — `auth.users`)
- LangGraph conversation checkpoints (`langgraph-checkpoint-postgres` managed tables)
- Thread metadata (titles, timestamps, user ownership)
- Document vector embeddings (pgvector `vector(1536)` columns)
- Long-term user memories with embeddings
- OAuth token storage (encrypted)
- Row Level Security (RLS) enforcing user isolation

### 2.4 MCP Servers (Remote)

**Responsibilities:**
- Expose external service capabilities as MCP tools
- Handle API-specific authentication and rate limiting
- Return structured results the agent can reason over

**Servers planned:**
| Server | Transport | Auth | Tools exposed |
|--------|-----------|------|---------------|
| Google Drive | HTTP via mcp-remote | OAuth 2.0 (per-user) | search_files, read_file, create_file, list_recent |
| GitHub | stdio via mcp-remote | OAuth / PAT (per-user) | search_repos, read_file, list_issues, create_issue, list_prs |

---

## 3. Communication Protocols

### 3.1 Frontend <-> Backend

| Pattern | Protocol | Use case |
|---------|----------|----------|
| Request/response | HTTPS REST (JSON) | Thread CRUD, document upload, auth, memory listing |
| Streaming | SSE (`text/event-stream`) | Chat responses — token-by-token AI output + tool status events |

**Why SSE over WebSocket:**
- Simpler to implement (unidirectional server -> client)
- Works through Vercel's edge network without special config
- Vercel AI SDK's `useChat()` uses SSE natively
- Sufficient for chat — user sends one message, server streams one response

**SSE event format:**
```
event: token
data: {"content": "Hello"}

event: tool_start
data: {"tool": "tavily_search", "status": "running"}

event: tool_end
data: {"tool": "tavily_search", "status": "complete"}

event: done
data: {"thread_id": "abc-123"}
```

### 3.2 Backend <-> Database

| Protocol | Library | Use case |
|----------|---------|----------|
| PostgreSQL wire protocol | psycopg2 (sync) | Direct SQL queries for thread metadata, memories, tokens |
| PostgreSQL wire protocol | langgraph-checkpoint-postgres | Checkpoint read/write (managed by LangGraph) |
| Supabase REST API | supabase-py (optional) | Auth token verification, if not using JWT directly |

**Connection pooling:** Use psycopg2 connection pool (`psycopg2.pool.ThreadedConnectionPool`) with min=2, max=10 connections. Railway's hobby plan runs a single process, so this is sufficient.

### 3.3 Backend <-> MCP Servers

| Transport | Library | Use case |
|-----------|---------|----------|
| stdio (via mcp-remote proxy) | mcp Python SDK | Google Drive, GitHub — remote HTTP servers proxied through `npx mcp-remote` |

MCP client sessions are created per-user-request and torn down after the LangGraph invocation completes. No persistent MCP connections are maintained between requests.

### 3.4 Backend <-> OpenAI

| Protocol | Library | Use case |
|----------|---------|----------|
| HTTPS REST | langchain-openai (`ChatOpenAI`) | Chat completions (GPT-4o-mini) |
| HTTPS REST | langchain-openai (`OpenAIEmbeddings`) | Text embeddings (text-embedding-3-small) |

### 3.5 Backend <-> Tavily

| Protocol | Library | Use case |
|----------|---------|----------|
| HTTPS REST | tavily-python (via LangChain wrapper) | Web search queries |

---

## 4. Authentication Architecture

### 4.1 Flow

```
1. User signs up/logs in via Next.js frontend
2. Frontend calls Supabase Auth SDK directly (client-side)
3. Supabase returns JWT (access_token + refresh_token)
4. Frontend stores tokens in httpOnly cookies (via Next.js middleware)
5. Every API request to backend includes: Authorization: Bearer <access_token>
6. Backend validates JWT using Supabase's JWT secret (SUPABASE_JWT_SECRET)
7. Backend extracts user_id from JWT claims
8. All database queries scoped by user_id
```

### 4.2 JWT Validation (Backend)

The backend validates JWTs independently — it does NOT call Supabase on every request. It uses the shared JWT secret to verify the signature locally.

```
JWT payload:
{
  "sub": "user-uuid",          <- user_id
  "email": "user@example.com",
  "role": "authenticated",
  "iat": 1700000000,
  "exp": 1700003600            <- 1 hour expiry
}
```

### 4.3 OAuth for MCP (Google Drive, GitHub)

Separate from Supabase Auth. These are service-specific OAuth flows managed by the backend:

```
1. User clicks "Connect Google Drive" in settings page
2. Frontend navigates to: GET /api/auth/connect/google
3. Backend generates Google OAuth URL with:
   - client_id (from Google Cloud Console)
   - redirect_uri: https://<backend>/api/auth/callback/google
   - scopes: ['https://www.googleapis.com/auth/drive.readonly']
   - state: encrypted(user_id + nonce)
4. User consents on Google's page
5. Google redirects to backend callback with auth code
6. Backend exchanges code for tokens
7. Tokens encrypted and stored in user_oauth_tokens table
8. Backend redirects to frontend settings page with success flag
```

---

## 5. Data Flow Diagrams

### 5.1 Chat Message (Happy Path)

```
User                Frontend              Backend                    Supabase        OpenAI
 |                     |                     |                          |               |
 |-- type message ---->|                     |                          |               |
 |                     |-- POST /api/chat -->|                          |               |
 |                     |   {thread_id, msg}  |                          |               |
 |                     |                     |-- validate JWT --------->|               |
 |                     |                     |<-- user_id --------------|               |
 |                     |                     |                          |               |
 |                     |                     |-- recall memories ------>|               |
 |                     |                     |<-- [memory1, memory2] ---|               |
 |                     |                     |                          |               |
 |                     |                     |-- load MCP tools ------->| (check tokens)|
 |                     |                     |                          |               |
 |                     |                     |-- LangGraph invoke ------|-------------->|
 |                     |                     |   (stream mode)          |               |
 |                     |<---- SSE: token ----|<--- token ---------------|-------------- |
 |<-- render token ----|                     |                          |               |
 |                     |<---- SSE: token ----|<--- token ---------------|-------------->|
 |<-- render token ----|                     |                          |               |
 |                     |                     |                          |               |
 |                     |                     |-- checkpoint save ------>|               |
 |                     |<---- SSE: done -----|                          |               |
 |<-- message done ----|                     |                          |               |
```

### 5.2 PDF Upload + RAG Query

```
User                Frontend              Backend                    Supabase
 |                     |                     |                          |
 |-- drag PDF -------->|                     |                          |
 |                     |-- POST /api/docs -->|                          |
 |                     |   (multipart file)  |                          |
 |                     |                     |-- PyPDF: extract text -->|               
 |                     |                     |-- split into chunks ---->|               
 |                     |                     |-- embed chunks -------->| (OpenAI)      
 |                     |                     |-- INSERT vectors ------>|               
 |                     |<-- 200 {metadata} --|                          |
 |<-- "PDF indexed" ---|                     |                          |
 |                     |                     |                          |
 |-- "What does it say about X?" ----------->|                          |
 |                     |                     |-- vector similarity --->|
 |                     |                     |<-- top 4 chunks --------|
 |                     |                     |-- LLM with context ---->| (OpenAI)
 |                     |<---- SSE: answer ---|                          |
```

---

## 6. Deployment Architecture

### 6.1 Vercel (Frontend)

```
GitHub repo (main branch)
    |
    | auto-deploy on push
    v
Vercel Build
    |-- next build (SSR + static)
    |-- output: .vercel/output
    v
Vercel Edge Network (CDN)
    |-- static assets cached globally
    |-- SSR pages on serverless functions
    |-- API routes proxy to Railway backend (via next.config.js rewrites)
```

**Environment variables on Vercel:**
| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://sam-api-production.up.railway.app` |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://<ref>.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase publishable anon key |

### 6.2 Railway (Backend)

```
GitHub repo (main branch)
    |
    | auto-deploy on push
    v
Railway Build
    |-- pip install -r requirements.txt
    |-- start: uvicorn main:app --host 0.0.0.0 --port $PORT
    v
Railway Container (always-on)
    |-- single process
    |-- persistent (no cold starts on hobby plan)
    |-- $PORT assigned by Railway
```

**Environment variables on Railway:**
| Variable | Value |
|----------|-------|
| `SUPABASE_DB_URL` | `postgresql://...@db.<ref>.supabase.co:5432/postgres` |
| `SUPABASE_JWT_SECRET` | JWT secret from Supabase dashboard |
| `OPENAI_API_KEY` | OpenAI key |
| `TAVILY_API_KEY` | Tavily key |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GITHUB_CLIENT_ID` | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth App client secret |
| `ENCRYPTION_KEY` | For encrypting stored OAuth tokens |
| `FRONTEND_URL` | `https://sam-ai.vercel.app` (for CORS + redirects) |

### 6.3 Supabase (Database)

Managed service — no deployment needed. Configuration via Supabase dashboard:
- Enable pgvector extension
- Create tables via SQL migrations
- Configure RLS policies
- Set up Auth providers (email, Google OAuth)

---

## 7. Security Architecture

### 7.1 Transport Security

- All traffic over HTTPS (TLS 1.3)
- Vercel and Railway provide automatic TLS certificates
- Supabase connections use SSL by default

### 7.2 Authentication & Authorization

| Layer | Mechanism |
|-------|-----------|
| Frontend -> Backend | JWT Bearer token in Authorization header |
| Backend JWT validation | Local signature check using SUPABASE_JWT_SECRET |
| Database access | Backend uses service role key (server-side only) |
| Data isolation | RLS policies on all user-scoped tables |
| MCP OAuth tokens | AES-256 encrypted at rest in user_oauth_tokens |

### 7.3 CORS Policy

Backend allows requests only from the frontend origin:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ["FRONTEND_URL"]],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 7.4 Rate Limiting

Backend applies per-user rate limits:
| Endpoint | Limit |
|----------|-------|
| `POST /api/chat` | 30 requests/minute |
| `POST /api/documents/upload` | 5 uploads/minute |
| All other endpoints | 60 requests/minute |

### 7.5 Input Validation

- All request bodies validated with Pydantic models
- File uploads: max 20MB, PDF only (MIME type + magic bytes check)
- Thread IDs: UUID format validation
- Text inputs: max length enforcement (messages: 10,000 chars)

---

## 8. Error Handling Strategy

### 8.1 Backend Error Responses

All errors return consistent JSON:
```json
{
  "error": {
    "code": "THREAD_NOT_FOUND",
    "message": "No thread found with the given ID.",
    "status": 404
  }
}
```

### 8.2 Error Categories

| Category | HTTP status | Handling |
|----------|------------|----------|
| Validation error | 422 | Frontend shows field-level errors |
| Auth error (expired JWT) | 401 | Frontend refreshes token, retries |
| Auth error (invalid JWT) | 401 | Frontend redirects to login |
| Not found | 404 | Frontend shows "not found" state |
| Rate limited | 429 | Frontend shows "slow down" message with retry-after |
| OpenAI error | 502 | Backend retries once, then returns error to frontend |
| MCP server error | 502 | Agent continues without that tool, notes it in response |
| Database error | 500 | Backend logs, returns generic error |

### 8.3 SSE Error Handling

During streaming, errors are sent as SSE events:
```
event: error
data: {"code": "LLM_ERROR", "message": "OpenAI rate limit exceeded. Please try again in a moment."}
```

Frontend catches error events and displays them inline in the chat.

---

## 9. Observability

### 9.1 Logging

Backend logs structured JSON to stdout (Railway captures and displays):
```json
{
  "timestamp": "2026-11-21T10:00:00Z",
  "level": "INFO",
  "event": "chat_request",
  "user_id": "uuid",
  "thread_id": "uuid",
  "tools_used": ["tavily_search"],
  "latency_ms": 2340
}
```

### 9.2 Monitoring

| Metric | Source |
|--------|--------|
| Frontend performance | Vercel Analytics (built-in) |
| Backend uptime | Railway metrics dashboard |
| Database performance | Supabase dashboard (query stats, connection count) |
| API latency | Custom middleware logging p50/p95/p99 |
| Error rate | Structured log aggregation |

---

## 10. Scalability Considerations

Current architecture targets **single-user to low-traffic** usage. For future scaling:

| Bottleneck | Current | Scale path |
|-----------|---------|------------|
| Backend concurrency | Single uvicorn process | Add workers: `uvicorn main:app --workers 4` |
| Database connections | psycopg2 pool (2-10) | Supabase connection pooler (PgBouncer built-in) |
| MCP server startups | Per-request spawn | Connection pool with TTL |
| Vector search | pgvector brute-force | Add IVFFlat or HNSW index as data grows |
| PDF processing | Synchronous in request | Background task queue (Celery/ARQ) |

These are not needed for v2 launch but documented for when load increases.
