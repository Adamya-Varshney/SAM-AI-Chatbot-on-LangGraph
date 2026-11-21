# SAM AI Chatbot v2 — API Contract Spec

**Version:** 1.0
**Date:** 2026-11-21
**Parent:** [01-PRD.md](./01-PRD.md)

---

## 1. Overview

The backend exposes a REST + SSE API over HTTPS. Base URL: `https://<railway-host>/api`

**Common headers on every request:**
```
Authorization: Bearer <supabase-jwt>
Content-Type: application/json  (except file uploads)
```

**Common error response:**
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description.",
    "status": 400
  }
}
```

---

## 2. Auth Endpoints

Authentication is handled client-side by Supabase Auth SDK. The backend provides OAuth connection endpoints for MCP integrations.

### 2.1 GET /api/auth/me

Returns the current authenticated user's profile.

**Response 200:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "created_at": "2026-11-21T10:00:00Z"
}
```

**Response 401:** Invalid or expired JWT.

---

### 2.2 GET /api/auth/connections

Lists the user's connected OAuth providers for MCP.

**Response 200:**
```json
{
  "connections": [
    {
      "provider": "google",
      "connected": true,
      "scopes": ["drive.readonly"],
      "connected_at": "2026-11-21T10:00:00Z"
    },
    {
      "provider": "github",
      "connected": false,
      "scopes": [],
      "connected_at": null
    }
  ]
}
```

---

### 2.3 GET /api/auth/connect/{provider}

Initiates OAuth flow. Redirects the browser to the provider's consent screen.

**Path params:** `provider` — `google` or `github`

**Response 302:** Redirect to provider's OAuth URL with:
- `client_id`
- `redirect_uri`: `/api/auth/callback/{provider}`
- `scope`: provider-specific scopes
- `state`: encrypted(user_id + nonce + timestamp)

---

### 2.4 GET /api/auth/callback/{provider}

OAuth callback handler. Exchanges auth code for tokens, stores them, redirects to frontend.

**Query params:**
- `code` — authorization code from provider
- `state` — encrypted state from the initial redirect

**Response 302:** Redirect to `{FRONTEND_URL}/settings?connected={provider}`

**Error:** Redirect to `{FRONTEND_URL}/settings?error=oauth_failed&provider={provider}`

---

### 2.5 DELETE /api/auth/disconnect/{provider}

Removes the OAuth connection and deletes stored tokens.

**Path params:** `provider` — `google` or `github`

**Response 200:**
```json
{
  "provider": "google",
  "disconnected": true
}
```

---

## 3. Chat Endpoints

### 3.1 POST /api/chat

Send a message and stream the AI response via SSE.

**Request:**
```json
{
  "thread_id": "uuid-string",
  "message": "What is the capital of France?",
  "location": "Noida, India",
  "timezone": "Asia/Kolkata"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| thread_id | string | yes | UUID format |
| message | string | yes | 1-10,000 characters |
| location | string | no | max 200 characters |
| timezone | string | no | valid IANA timezone |

**Response:** `200 OK` with `Content-Type: text/event-stream`

**SSE events:**

```
event: token
data: {"content": "The"}

event: token
data: {"content": " capital"}

event: token
data: {"content": " of France is Paris."}

event: tool_start
data: {"tool": "tavily_search_results_json", "label": "Searching the web..."}

event: tool_end
data: {"tool": "tavily_search_results_json", "label": "Search complete"}

event: memory_stored
data: {"content": "User is interested in geography"}

event: done
data: {"thread_id": "uuid", "title": "Capital of France", "title_generated": true}

event: error
data: {"code": "LLM_ERROR", "message": "OpenAI rate limit. Try again in a moment."}
```

**Event types:**

| Event | Frequency | Purpose |
|-------|-----------|---------|
| `token` | Many per response | Incremental AI text |
| `tool_start` | 0-N per response | Agent started using a tool |
| `tool_end` | 0-N per response | Tool call completed |
| `memory_stored` | 0-N per response | Agent stored a long-term memory |
| `done` | Exactly 1 | Stream complete, includes metadata |
| `error` | 0-1 | Fatal error during generation |

**Thread auto-creation:** If `thread_id` doesn't exist in `thread_metadata`, the backend creates it on the first message. The `done` event includes `title_generated: true` when a title was auto-generated.

---

### 3.2 POST /api/chat/title

Regenerate a thread's title from its first exchange.

**Request:**
```json
{
  "thread_id": "uuid-string"
}
```

**Response 200:**
```json
{
  "thread_id": "uuid-string",
  "title": "Capital of France"
}
```

---

## 4. Thread Endpoints

### 4.1 GET /api/threads

List the authenticated user's conversations, newest first.

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| limit | integer | 50 | Max threads to return (1-100) |
| offset | integer | 0 | Pagination offset |

**Response 200:**
```json
{
  "threads": [
    {
      "thread_id": "uuid-1",
      "title": "Capital of France",
      "created_at": "2026-11-21T10:00:00Z",
      "updated_at": "2026-11-21T10:05:00Z",
      "has_document": true
    },
    {
      "thread_id": "uuid-2",
      "title": "Python Debugging Help",
      "created_at": "2026-11-20T08:00:00Z",
      "updated_at": "2026-11-20T08:30:00Z",
      "has_document": false
    }
  ],
  "total": 15,
  "limit": 50,
  "offset": 0
}
```

---

### 4.2 GET /api/threads/{thread_id}

Get full message history for a thread.

**Response 200:**
```json
{
  "thread_id": "uuid-1",
  "title": "Capital of France",
  "created_at": "2026-11-21T10:00:00Z",
  "messages": [
    {
      "role": "user",
      "content": "What is the capital of France?",
      "timestamp": "2026-11-21T10:00:01Z"
    },
    {
      "role": "assistant",
      "content": "The capital of France is **Paris**.",
      "timestamp": "2026-11-21T10:00:03Z",
      "tools_used": []
    }
  ],
  "document": {
    "filename": "report.pdf",
    "page_count": 12,
    "chunk_count": 48,
    "uploaded_at": "2026-11-21T10:00:00Z"
  }
}
```

**Response 404:** Thread not found or belongs to another user.

---

### 4.3 PATCH /api/threads/{thread_id}

Rename a thread.

**Request:**
```json
{
  "title": "French Geography"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| title | string | yes | 1-200 characters |

**Response 200:**
```json
{
  "thread_id": "uuid-1",
  "title": "French Geography"
}
```

---

### 4.4 DELETE /api/threads/{thread_id}

Delete a thread and all associated data (checkpoints, documents, vectors).

**Response 200:**
```json
{
  "thread_id": "uuid-1",
  "deleted": true
}
```

---

## 5. Document Endpoints

### 5.1 POST /api/documents/upload

Upload and ingest a PDF for RAG.

**Request:** `Content-Type: multipart/form-data`

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| file | binary | yes | PDF, max 20MB |
| thread_id | string | yes | UUID format |

**Response 200:**
```json
{
  "filename": "report.pdf",
  "thread_id": "uuid-1",
  "page_count": 12,
  "chunk_count": 48,
  "file_size": 1048576
}
```

**Response 413:** File too large (>20MB).
**Response 415:** Not a valid PDF.
**Response 409:** This PDF already ingested for this thread.

---

### 5.2 GET /api/documents/{thread_id}

List documents ingested for a thread.

**Response 200:**
```json
{
  "documents": [
    {
      "id": "uuid",
      "filename": "report.pdf",
      "page_count": 12,
      "chunk_count": 48,
      "file_size": 1048576,
      "uploaded_at": "2026-11-21T10:00:00Z"
    }
  ]
}
```

---

### 5.3 DELETE /api/documents/{document_id}

Delete a document and its vector chunks.

**Response 200:**
```json
{
  "id": "uuid",
  "deleted": true
}
```

---

## 6. Memory Endpoints

### 6.1 GET /api/memories

List the user's long-term memories.

**Query params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| category | string | (all) | Filter by category |
| limit | integer | 50 | Max memories (1-200) |
| offset | integer | 0 | Pagination offset |

**Response 200:**
```json
{
  "memories": [
    {
      "id": "uuid",
      "content": "User prefers dark mode",
      "category": "preference",
      "created_at": "2026-11-21T10:00:00Z"
    },
    {
      "id": "uuid",
      "content": "User is building a chatbot with LangGraph",
      "category": "project",
      "created_at": "2026-11-20T08:00:00Z"
    }
  ],
  "total": 12,
  "limit": 50,
  "offset": 0
}
```

---

### 6.2 DELETE /api/memories/{memory_id}

Delete a specific memory.

**Response 200:**
```json
{
  "id": "uuid",
  "deleted": true
}
```

**Response 404:** Memory not found or belongs to another user.

---

## 7. Health Endpoint

### 7.1 GET /api/health

Public endpoint (no auth). Used by Railway and monitoring.

**Response 200:**
```json
{
  "status": "ok",
  "version": "2.0.0",
  "database": "connected",
  "timestamp": "2026-11-21T10:00:00Z"
}
```

**Response 503:** Database unreachable.

---

## 8. Rate Limits

Applied per authenticated user via middleware:

| Endpoint pattern | Limit | Window |
|-----------------|-------|--------|
| `POST /api/chat` | 30 | 1 minute |
| `POST /api/documents/upload` | 5 | 1 minute |
| `POST /api/chat/title` | 10 | 1 minute |
| All other endpoints | 60 | 1 minute |

**Rate limit response (429):**
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Try again in 15 seconds.",
    "status": 429,
    "retry_after": 15
  }
}
```

Headers on every response:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 28
X-RateLimit-Reset: 1700000060
```

---

## 9. Pagination Convention

All list endpoints use offset-based pagination:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| limit | integer | 50 | Items per page |
| offset | integer | 0 | Skip this many items |

Response always includes:
```json
{
  "items": [...],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

---

## 10. Versioning

The API has no version prefix in v2 (`/api/chat`, not `/api/v2/chat`). If a breaking change is needed in future, the prefix `/api/v3/` will be introduced while maintaining `/api/` as v2 for backwards compatibility.
