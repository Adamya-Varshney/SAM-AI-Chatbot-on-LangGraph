# SAM AI Chatbot v2 — Product Requirements Document

**Version:** 1.0
**Date:** 2026-11-21
**Author:** Adamya Varshney

---

## 1. Project Overview

SAM is a multi-utility AI assistant built on LangGraph with OpenAI GPT-4o-mini. The current version (v1) runs as a monolithic Streamlit application hosted on Streamlit Cloud. Version 2 migrates SAM to a modern full-stack architecture with a React frontend, a persistent API backend, cloud-hosted database, user authentication, and MCP-based external tool integrations.

### 1.1 Current State (v1)

| Layer | Technology | Limitation |
|-------|-----------|------------|
| Frontend | Streamlit (Python) | Widget-based UI, no custom components, limited styling control |
| Backend | LangGraph + LangChain (in-process) | Coupled to frontend, no API boundary |
| Database | SQLite (local file) | Wiped on Streamlit Cloud container restart |
| Hosting | Streamlit Cloud (free) | Ephemeral filesystem, sleeps after inactivity, no custom domain |
| Auth | None | No user accounts, all threads shared in one pool |
| External tools | Tavily (web search), PDF RAG (FAISS in-memory) | FAISS vectors lost on restart, no persistent document store |

### 1.2 Existing Capabilities to Preserve

All v1 features must work in v2 with no regressions:

- **Conversational AI**: Multi-turn chat with GPT-4o-mini via LangGraph agentic loop (chat_node <-> tools)
- **PDF Q&A (RAG)**: Upload PDF, chunk with RecursiveCharacterTextSplitter, embed with text-embedding-3-small, retrieve with FAISS similarity search
- **Web search**: Tavily search with max 3 results
- **Code interpreter**: Python code generation, explanation, and step-by-step tracing (prompt-based, not sandboxed execution)
- **Conversation persistence**: Thread-based checkpointing with auto-generated titles
- **Conversation management**: Create, switch, rename threads via sidebar
- **Location/timezone awareness**: User-configurable location and timezone injected into system prompt
- **Streaming responses**: Token-by-token display with tool-use status indicators

---

## 2. Goals

### 2.1 Primary Goals

1. **Modern UI**: Replace Streamlit with a Next.js React frontend matching the design language of ChatGPT/Claude/Perplexity — centered chat column, collapsible sidebar, streaming markdown, code blocks with syntax highlighting, dark/light mode
2. **Persistent backend API**: FastAPI server wrapping LangGraph, deployed on a persistent host (Railway), decoupled from the frontend
3. **Cloud database**: Migrate SQLite to Supabase PostgreSQL with pgvector for durable conversation checkpoints and vector embeddings
4. **User authentication**: Supabase Auth with email/password and OAuth providers, so each user has private conversations and data
5. **User-specific memory**: Two-layer memory system — per-thread conversation checkpoints (existing, migrated) and cross-conversation long-term memory (new) scoped by user
6. **MCP tool integration**: Google Drive and GitHub access via MCP servers with per-user OAuth tokens
7. **Reliable hosting**: Frontend on Vercel (always available, no sleep), backend on Railway (always-on process)

### 2.2 Non-Goals (v2)

- Sandboxed code execution (code interpreter remains prompt-based)
- Real-time collaboration (multi-user in same thread)
- Mobile native app (responsive web is sufficient)
- Self-hosted MCP servers (use existing remote/community servers)
- Voice input/output
- Image generation

### 2.3 Future Versions (v3+)

- **Zomato MCP integration**: Restaurant discovery, menu browsing, cart creation, food ordering, QR code payment via Zomato's hosted MCP server (`https://mcp-server.zomato.com/mcp`). Requires Zomato developer access approval and OAuth redirect URI whitelisting.
- Additional MCP servers (Notion, Slack, Calendar)
- Admin dashboard for usage analytics
- Team/organization accounts

---

## 3. User Stories

### Authentication

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| U-01 | As a new user, I can sign up with email/password | Account created in Supabase Auth, redirected to chat |
| U-02 | As a returning user, I can log in and see my conversations | JWT issued, threads loaded for my user_id only |
| U-03 | As a user, I can sign in with Google OAuth | Google OAuth flow completes, account linked |
| U-04 | As a user, I can sign out | JWT cleared, redirected to login page |

### Chat

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| C-01 | As a user, I can send a message and see a streaming response | Tokens appear incrementally via SSE, full markdown rendered on completion |
| C-02 | As a user, I can start a new conversation | New thread_id created, empty chat view shown |
| C-03 | As a user, I can switch between my conversations in the sidebar | Messages load from PostgreSQL checkpointer, chat view updates |
| C-04 | As a user, I can rename a conversation | Title updated in thread_metadata table |
| C-05 | As a user, I can delete a conversation | Thread and its checkpoints removed from database |
| C-06 | As a user, I see an auto-generated title after my first message | LLM generates a 5-word title, saved to thread_metadata |
| C-07 | As a user, I see tool usage indicators while the agent works | Status pill shows "Searching web...", "Reading PDF...", etc. |

### PDF RAG

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| R-01 | As a user, I can upload a PDF via drag-and-drop | PDF accepted, ingestion starts with progress indicator |
| R-02 | As a user, I can ask questions about my uploaded PDF | rag_tool retrieves relevant chunks, LLM answers with citations |
| R-03 | As a user, my PDF vectors persist across sessions | Vectors stored in pgvector, available on next login |
| R-04 | As a user, my PDFs are private to my account | Vectors tagged with user_id, queries filtered by user |

### Memory

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| M-01 | As a user, my conversation history persists across browser sessions | PostgreSQL checkpointer retains full message history |
| M-02 | As a user, SAM remembers facts about me across conversations | Long-term memories stored in user_memories table, recalled via embedding similarity |
| M-03 | As a user, SAM uses what it knows about me to personalize responses | Relevant memories injected into system prompt at each turn |
| M-04 | As a user, I can ask SAM to forget something | Specific memory deleted from user_memories |

### MCP Tools

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| T-01 | As a user, I can connect my Google Drive | OAuth flow completes, tokens stored securely |
| T-02 | As a user, I can ask SAM to search/read my Google Drive files | Google Drive MCP tools available to the agent when connected |
| T-03 | As a user, I can connect my GitHub account | OAuth flow completes, tokens stored securely |
| T-04 | As a user, I can ask SAM about my GitHub repos, issues, PRs | GitHub MCP tools available to the agent when connected |
| T-05 | As a user, my OAuth tokens are private and secure | Tokens encrypted at rest, scoped per user, refreshed automatically |

### UI/UX

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| X-01 | As a user, I see a modern chat interface on first visit | Centered chat column, welcome screen with capability cards, suggested prompts |
| X-02 | As a user, I can toggle dark/light mode | Theme persists across sessions via localStorage |
| X-03 | As a user, the app works well on mobile | Sidebar collapses to hamburger, chat fills viewport, input stays sticky |
| X-04 | As a user, I see syntax-highlighted code blocks with copy buttons | Code blocks rendered with rehype-highlight, copy icon on hover |
| X-05 | As a user, I see my connected integrations in the sidebar | Google Drive, GitHub shown with connected/disconnected status |

---

## 4. Tech Stack

### Frontend

| Technology | Purpose | Version |
|-----------|---------|---------|
| Next.js (App Router) | React framework, SSR + client components | 14+ |
| Tailwind CSS | Utility-first styling | 3.x |
| shadcn/ui | Pre-built UI components (Button, Dialog, Sidebar, etc.) | latest |
| Vercel AI SDK (`ai`) | `useChat()` hook for SSE streaming | 3.x |
| react-markdown + rehype-highlight | Markdown rendering with syntax highlighting | latest |
| next-themes | Dark/light mode toggle | latest |
| Framer Motion | Animations (message entry, sidebar slide) | latest |
| Geist font | Typography via next/font | latest |
| Lucide React | Icon library | latest |

### Backend

| Technology | Purpose | Version |
|-----------|---------|---------|
| FastAPI | HTTP API framework | 0.110+ |
| Uvicorn | ASGI server | latest |
| LangGraph | Agentic orchestration (StateGraph) | latest |
| LangChain + LangChain-OpenAI | LLM interface, tool framework | latest |
| langgraph-checkpoint-postgres | PostgreSQL checkpointer | latest |
| psycopg2-binary | PostgreSQL driver | latest |
| python-jose[cryptography] | JWT validation | latest |
| mcp (Python SDK) | MCP client for Google Drive + GitHub servers | latest |
| Tavily Python | Web search API | latest |
| PyPDF + langchain-text-splitters | PDF loading and chunking | latest |

### Infrastructure

| Service | Plan | Purpose |
|---------|------|---------|
| Vercel | Hobby (free) | Frontend hosting + CDN |
| Railway | Hobby (~$5-8/mo) | Backend hosting (always-on) |
| Supabase | Pro ($25/mo) | PostgreSQL + pgvector + Auth + Row Level Security |
| OpenAI | Pay-per-use | GPT-4o-mini (chat) + text-embedding-3-small (embeddings) |
| Tavily | Free tier | Web search (1,000 searches/mo) |
| Google Cloud Console | Free | OAuth credentials for Google Drive |
| GitHub | Free | OAuth App for GitHub MCP |

---

## 5. Architecture

### 5.1 High-Level

```
User (Browser)
    |
    | HTTPS
    v
Next.js Frontend (Vercel)
    |
    | REST + SSE
    v
FastAPI Backend (Railway)
    |
    |--- LangGraph Agent (chat_node <-> tools)
    |       |--- Tavily (web search)
    |       |--- rag_tool (PDF Q&A via pgvector)
    |       |--- remember / recall_memories (long-term memory)
    |       |--- Google Drive tools (via MCP client)
    |       |--- GitHub tools (via MCP client)
    |
    |--- Supabase PostgreSQL
    |       |--- auth.users (Supabase Auth)
    |       |--- langgraph checkpoints (conversation state)
    |       |--- thread_metadata (titles, timestamps)
    |       |--- user_memories (long-term facts + embeddings)
    |       |--- document_chunks (PDF vectors via pgvector)
    |       |--- user_oauth_tokens (encrypted Google/GitHub tokens)
    |
    |--- MCP Servers (remote)
            |--- Google Drive MCP (user's OAuth token)
            |--- GitHub MCP (user's OAuth token)
```

### 5.2 Request Flow — Chat Message

```
1. User types message in Next.js UI
2. Frontend POST /api/chat with { thread_id, message, user_token }
3. Backend validates JWT, extracts user_id
4. Backend loads user-specific tools (base + connected MCP tools)
5. Backend recalls relevant long-term memories for this user
6. Backend invokes LangGraph graph with:
   - messages: [SystemMessage (with memories), ...history, HumanMessage]
   - config: { thread_id, user_id }
7. LangGraph runs chat_node -> tools -> chat_node loop
8. Each AI token streamed back via SSE
9. Checkpointer auto-saves state to PostgreSQL
10. Frontend renders streaming markdown
11. On first message: backend generates title, saves to thread_metadata
```

### 5.3 Request Flow — OAuth Connection

```
1. User clicks "Connect Google Drive" in frontend
2. Frontend redirects to GET /api/auth/connect/google
3. Backend builds Google OAuth URL with scopes [drive.readonly]
4. User consents on Google's page
5. Google redirects to /api/auth/callback/google?code=...
6. Backend exchanges code for access_token + refresh_token
7. Tokens encrypted and stored in user_oauth_tokens
8. Backend redirects to frontend with success status
9. Next chat invocation loads Google Drive MCP tools for this user
```

---

## 6. API Endpoints (Summary)

Detailed request/response schemas are in spec 04 (API Contract).

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/signup` | Create account |
| POST | `/api/auth/login` | Email/password login, returns JWT |
| POST | `/api/auth/logout` | Invalidate session |
| GET | `/api/auth/me` | Current user profile |
| GET | `/api/auth/connect/{provider}` | Start OAuth flow (google, github) |
| GET | `/api/auth/callback/{provider}` | OAuth redirect handler |
| DELETE | `/api/auth/disconnect/{provider}` | Remove OAuth connection |
| GET | `/api/auth/connections` | List connected services |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send message, stream response (SSE) |
| POST | `/api/chat/title` | Generate title for a thread |

### Threads
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/threads` | List user's conversations |
| GET | `/api/threads/{id}` | Get thread messages |
| PATCH | `/api/threads/{id}` | Rename thread |
| DELETE | `/api/threads/{id}` | Delete thread + checkpoints |

### Documents
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/documents/upload` | Upload + ingest PDF |
| GET | `/api/documents/{thread_id}` | List documents for a thread |
| DELETE | `/api/documents/{id}` | Remove document + vectors |

### Memory
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/memories` | List user's long-term memories |
| DELETE | `/api/memories/{id}` | Delete a specific memory |

---

## 7. Database Tables (Summary)

Detailed schemas with column types, indexes, and RLS policies are in spec 03 (Database Schema).

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `auth.users` | Supabase managed auth | id, email, created_at |
| `thread_metadata` | Conversation titles | thread_id, user_id, title, created_at |
| `user_memories` | Long-term user facts | id, user_id, content, category, embedding (vector 1536) |
| `document_chunks` | PDF vector embeddings | id, user_id, thread_id, content, embedding (vector 1536), metadata |
| `user_oauth_tokens` | Encrypted OAuth tokens | id, user_id, provider, access_token, refresh_token, scopes |
| `langgraph checkpoints` | Managed by langgraph-checkpoint-postgres | (internal schema) |

---

## 8. Frontend Pages

| Route | Page | Auth required |
|-------|------|---------------|
| `/` | Chat interface (main) | Yes |
| `/login` | Login form | No |
| `/signup` | Signup form | No |
| `/settings` | User settings + connected integrations | Yes |

---

## 9. Migration Plan

### Phase 1: Database + Auth
- Set up Supabase project (already on Pro plan)
- Create tables with RLS policies
- Enable pgvector extension
- Configure Supabase Auth (email/password)
- **Deliverable:** Database ready, auth endpoints tested

### Phase 2: Backend API
- Create FastAPI project
- Migrate LangGraph graph (chat_node, tools, system prompt)
- Replace SqliteSaver with PostgresSaver
- Implement /api/chat with SSE streaming
- Implement /api/threads CRUD
- Implement /api/documents/upload with pgvector
- Deploy on Railway
- **Deliverable:** API serving chat with persistence, deployed

### Phase 3: Memory System
- Implement user_memories table + UserMemoryManager
- Add `remember` and `recall_memories` tools to agent
- Auto-recall relevant memories in chat_node
- Implement /api/memories endpoints
- **Deliverable:** Agent remembers facts across conversations

### Phase 4: Frontend
- Initialize Next.js project with Tailwind + shadcn/ui
- Build chat UI (message list, streaming, code blocks)
- Build sidebar (conversations, PDF upload, settings)
- Build auth pages (login, signup)
- Connect to backend API with Vercel AI SDK
- Implement dark/light mode
- Deploy on Vercel
- **Deliverable:** Modern UI fully functional, deployed

### Phase 5: MCP Tooling
- Create Google Cloud OAuth credentials
- Create GitHub OAuth App
- Implement OAuth flows in backend
- Implement MCP client with mcp-remote adapter
- Build MCP-to-LangChain tool adapter
- Dynamic tool loading per user session
- Build settings page for managing connections
- **Deliverable:** Users can connect Drive + GitHub, agent uses them

### Phase 6: Integration + Polish
- End-to-end testing all features
- Performance optimization (connection pooling, caching)
- Error handling and edge cases
- Migrate existing v1 data if needed
- Decommission Streamlit app
- **Deliverable:** Production-ready v2

---

## 10. Success Criteria

| Criteria | Measurement |
|----------|-------------|
| No feature regressions from v1 | All v1 capabilities work in v2 |
| Conversations persist across sessions | User logs out, logs back in, all threads intact |
| Sub-second initial page load | Measured via Vercel Analytics |
| Streaming latency < 500ms to first token | From message send to first SSE event |
| PDF vectors persist across restarts | Upload PDF, restart backend, query still works |
| Long-term memory works cross-thread | Store fact in thread A, recall it in thread B |
| MCP tools functional | Search Google Drive, read GitHub repo via chat |
| Mobile responsive | Usable on 375px viewport width |

---

## 11. Constraints and Risks

| Risk | Mitigation |
|------|-----------|
| Railway free trial expires | Hobby plan at ~$5-8/mo is the minimum viable cost |
| Supabase free tier DB limit (500MB) | Already on Pro plan (8GB) |
| Tavily free tier limit (1,000/mo) | Monitor usage, upgrade if needed |
| Google Drive MCP server availability | Use community-maintained server, have fallback |
| GitHub MCP server availability | Official MCP server exists and is maintained |
| LangGraph streaming over HTTP | Use SSE (Server-Sent Events), well-supported pattern |
| OAuth token expiry | Implement automatic refresh with refresh_token |
| Cold start on Railway | Hobby plan keeps process running, no cold starts |

---

## 12. Out-of-Scope Decisions (Deferred)

These decisions will be made in the relevant spec documents:

- Exact Supabase RLS policy definitions (spec 03)
- API request/response JSON schemas (spec 04)
- JWT validation strategy — Supabase client-side vs backend verification (spec 05)
- Component prop interfaces and state management approach (spec 06)
- Memory recall scoring threshold and max memories per prompt (spec 07)
- MCP server lifecycle management — per-request vs connection pool (spec 08)
