# SAM AI Chatbot v2 — MCP Integration Spec

**Version:** 1.0
**Date:** 2026-11-21
**Parent:** [01-PRD.md](./01-PRD.md)

---

## 1. Overview

SAM AI integrates external services as tools via the **Model Context Protocol (MCP)**. MCP provides a standardized way for LLM applications to connect to external data sources and tools.

**v2 integrations:**
| Server | Purpose | Transport | Auth |
|--------|---------|-----------|------|
| Google Drive | Search, read, list files in user's Drive | HTTP via mcp-remote | OAuth 2.0 (per-user) |
| GitHub | Browse repos, read files, list issues/PRs | HTTP via mcp-remote | OAuth 2.0 (per-user) |

**Future (v3+):**
| Server | Purpose | Transport | Auth |
|--------|---------|-----------|------|
| Zomato | Restaurant search, ordering, tracking | HTTP (remote hosted) | OAuth 2.0 (per-user) |

---

## 2. Architecture

### 2.1 MCP in the LangGraph Agent

MCP servers expose **tools** that the LangGraph agent can call. The agent sees them as regular LangChain tools alongside built-in tools (Tavily search, RAG retrieval).

```
┌─────────────────────────────────────────────────┐
│                 LangGraph Agent                  │
│                                                  │
│  Built-in tools:         MCP tools:              │
│  ├─ tavily_search        ├─ gdrive_search_files  │
│  ├─ rag_retrieval        ├─ gdrive_read_file     │
│  └─ store_memory         ├─ github_search_repos  │
│                          ├─ github_read_file     │
│                          └─ github_list_issues   │
│                                                  │
│  All tools registered in the same tool list.     │
│  The LLM decides which tool to call.             │
└─────────────────────────────────────────────────┘
```

### 2.2 Transport: mcp-remote

Both Google Drive and GitHub MCP servers are remote HTTP servers. The MCP Python SDK's `StdioServerParameters` expects a stdio-based server. The `mcp-remote` npm package bridges this gap:

```
Backend (Python)                     mcp-remote (Node.js)              MCP Server (HTTP)
     |                                      |                               |
     |-- stdio (stdin/stdout) ------------>|                               |
     |                                      |-- HTTPS POST /mcp ---------->|
     |                                      |<-- JSON response ------------|
     |<-- stdio response ------------------|                               |
```

`mcp-remote` is an npm package that proxies a remote HTTP MCP server as a local stdio server, which the Python MCP SDK can connect to.

### 2.3 Per-User Tool Loading

Not all users have connected Google Drive or GitHub. The backend dynamically loads MCP tools based on the user's connected providers:

```python
async def get_tools_for_user(user_id: str) -> list[BaseTool]:
    tools = [
        tavily_search_tool,
        rag_retrieval_tool,
        store_memory_tool,
    ]
    
    connections = await get_user_connections(user_id)
    
    if "google" in connections:
        google_token = await get_google_token(user_id)
        gdrive_tools = await load_mcp_tools("google-drive", google_token)
        tools.extend(gdrive_tools)
    
    if "github" in connections:
        github_token = await get_github_token(user_id)
        github_tools = await load_mcp_tools("github", github_token)
        tools.extend(github_tools)
    
    return tools
```

---

## 3. MCP Client Implementation

### 3.1 Client Session Lifecycle

MCP client sessions are created per-request and torn down after the LangGraph invocation completes:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def load_mcp_tools(server_name: str, auth_token: str) -> list[BaseTool]:
    server_config = MCP_SERVERS[server_name]
    
    server_params = StdioServerParameters(
        command="npx",
        args=[
            "mcp-remote",
            server_config["url"],
            "--header",
            f"Authorization: Bearer {auth_token}",
        ],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            mcp_tools = await session.list_tools()
            
            return [
                convert_mcp_tool_to_langchain(tool, session)
                for tool in mcp_tools.tools
            ]
```

### 3.2 Tool Conversion

MCP tools use JSON Schema for their input definitions. These are converted to LangChain-compatible tools:

```python
from langchain_core.tools import StructuredTool

def convert_mcp_tool_to_langchain(mcp_tool, session: ClientSession) -> BaseTool:
    async def call_mcp_tool(**kwargs):
        result = await session.call_tool(mcp_tool.name, kwargs)
        if result.isError:
            return f"Error: {result.content[0].text}"
        return result.content[0].text
    
    return StructuredTool.from_function(
        coroutine=call_mcp_tool,
        name=mcp_tool.name,
        description=mcp_tool.description,
        args_schema=json_schema_to_pydantic(mcp_tool.inputSchema),
    )
```

### 3.3 Session Management

Since MCP sessions involve spawning a child process (`npx mcp-remote`), they must be properly managed:

```python
class MCPSessionManager:
    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
    
    async def get_session(self, server_name: str, auth_token: str) -> ClientSession:
        key = f"{server_name}:{hash(auth_token)}"
        
        if key not in self._sessions:
            self._sessions[key] = await self._create_session(server_name, auth_token)
        
        return self._sessions[key]
    
    async def cleanup_session(self, key: str):
        if key in self._sessions:
            session = self._sessions.pop(key)
            await session.__aexit__(None, None, None)
    
    async def cleanup_all(self):
        for key in list(self._sessions.keys()):
            await self.cleanup_session(key)
```

**Lifecycle per request:**
1. User sends chat message
2. Backend checks user's connected providers
3. For each connected provider, create or reuse MCP session
4. Load tools from MCP sessions
5. Run LangGraph agent with all tools
6. After response completes, sessions can be reused or cleaned up

---

## 4. Server Configurations

### 4.1 Google Drive MCP Server

```python
MCP_SERVERS = {
    "google-drive": {
        "url": "https://mcp.googleapis.com/drive",  # or community server URL
        "transport": "http",
        "auth_type": "oauth_bearer",
        "tools_exposed": [
            "search_files",     # Search files by name or content
            "read_file",        # Read file contents (text, docs, sheets)
            "list_recent",      # List recently modified files
        ],
    },
}
```

**Expected tools from Google Drive MCP:**

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `search_files` | Search Google Drive files | `{ query: string, max_results?: number }` | File list with names, IDs, types |
| `read_file` | Read a file's content | `{ file_id: string }` | File text content |
| `list_recent` | List recently modified files | `{ max_results?: number }` | File list sorted by last modified |

### 4.2 GitHub MCP Server

```python
MCP_SERVERS["github"] = {
    "url": "https://api.githubcopilot.com/mcp",  # or community server URL
    "transport": "http",
    "auth_type": "oauth_bearer",
    "tools_exposed": [
        "search_repos",      # Search user's repositories
        "read_file",         # Read a file from a repo
        "list_issues",       # List issues in a repo
        "create_issue",      # Create a new issue
        "list_prs",          # List pull requests
    ],
}
```

**Expected tools from GitHub MCP:**

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `search_repos` | Search repositories | `{ query: string }` | Repo list with names, descriptions |
| `read_file` | Read file from repo | `{ owner: string, repo: string, path: string }` | File content |
| `list_issues` | List repo issues | `{ owner: string, repo: string, state?: string }` | Issue list |
| `create_issue` | Create an issue | `{ owner: string, repo: string, title: string, body: string }` | Created issue details |
| `list_prs` | List pull requests | `{ owner: string, repo: string, state?: string }` | PR list |

### 4.3 Zomato MCP Server (Future — v3+)

```python
# Deferred to v3+ — requires Zomato developer access approval
# and redirect URI whitelisting
MCP_SERVERS["zomato"] = {
    "url": "https://mcp-server.zomato.com/mcp",
    "transport": "http",
    "auth_type": "oauth",
    "auth_url": "https://www.zomato.com/oauth2/authorize",
    "token_url": "https://www.zomato.com/oauth2/token",
    "scopes": ["read", "order"],
    "tools_exposed": [
        "get_restaurants_for_keyword",
        "get_restaurant_menu_by_categories",
        "get_menu_items_listing",
        "create_cart",
        "checkout_cart",
        "get_order_history",
        "get_order_tracking_info",
    ],
    "notes": "Requires Zomato developer access. Redirect URI must be whitelisted by Zomato.",
}
```

---

## 5. Error Handling

### 5.1 MCP Server Unavailable

If an MCP server fails to connect, the agent continues without those tools:

```python
async def get_tools_for_user(user_id: str) -> list[BaseTool]:
    tools = [tavily_search_tool, rag_retrieval_tool, store_memory_tool]
    
    connections = await get_user_connections(user_id)
    
    for provider in connections:
        try:
            token = await get_provider_token(user_id, provider)
            mcp_tools = await asyncio.wait_for(
                load_mcp_tools(provider, token),
                timeout=10.0,  # 10 second timeout for MCP connection
            )
            tools.extend(mcp_tools)
        except (TimeoutError, ConnectionError, Exception) as e:
            logger.warning(f"MCP server {provider} unavailable: {e}")
            # Agent continues without this provider's tools
    
    return tools
```

### 5.2 Tool Call Failures

When an MCP tool call fails during agent execution:

```python
async def safe_mcp_tool_call(session, tool_name, arguments):
    try:
        result = await asyncio.wait_for(
            session.call_tool(tool_name, arguments),
            timeout=30.0,
        )
        if result.isError:
            return f"Tool error: {result.content[0].text}"
        return result.content[0].text
    except TimeoutError:
        return "Tool timed out. The external service may be slow. Try again later."
    except Exception as e:
        return f"Tool unavailable: {str(e)}"
```

The LLM receives the error message as the tool result and can:
- Explain the failure to the user
- Try an alternative approach
- Suggest the user check their connection

### 5.3 OAuth Token Expired

If a tool call fails with a 401, attempt a token refresh (Google) or inform the user (GitHub):

```python
async def handle_auth_error(user_id: str, provider: str):
    if provider == "google":
        new_token = await refresh_google_token(user_id)
        if new_token:
            return new_token  # Retry with new token
    
    # Token permanently invalid — user needs to reconnect
    raise OAuthExpiredError(
        f"Your {provider} connection has expired. "
        f"Please reconnect in Settings."
    )
```

---

## 6. SSE Events for MCP Tool Usage

When the agent uses an MCP tool, the backend sends SSE events:

```
event: tool_start
data: {"tool": "gdrive_search_files", "label": "Searching Google Drive..."}

event: tool_end
data: {"tool": "gdrive_search_files", "label": "Found 3 files"}
```

The `label` field uses human-readable descriptions mapped from tool names:

```python
TOOL_LABELS = {
    "search_files": "Searching Google Drive...",
    "read_file": "Reading file from Google Drive...",
    "search_repos": "Searching GitHub repositories...",
    "list_issues": "Listing GitHub issues...",
    "tavily_search_results_json": "Searching the web...",
}
```

---

## 7. Prerequisites and Setup

### 7.1 System Requirements

| Requirement | Purpose |
|------------|---------|
| Node.js 18+ | Required for `npx mcp-remote` |
| `mcp-remote` npm package | Proxies remote HTTP MCP servers as stdio |
| Python `mcp` SDK | MCP client library |

### 7.2 Backend Dependencies

```
mcp>=1.0.0
```

`mcp-remote` is invoked via `npx` and does not need to be installed globally. It's downloaded and cached on first use.

### 7.3 Railway Setup

The Railway deployment needs Node.js available alongside Python. Options:
1. **Nixpacks** (Railway's default builder) — detects both Python and Node.js from `requirements.txt` + `package.json`
2. **Custom Dockerfile** — install both runtimes explicitly

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y nodejs npm
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]
```

---

## 8. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Token in subprocess args | `mcp-remote` receives token via `--header` flag; process args are visible via `/proc` on Linux, but Railway containers are single-tenant |
| MCP server trust | Only connect to known, trusted MCP servers (Google, GitHub official or vetted community) |
| Tool output injection | Sanitize MCP tool outputs before passing to LLM (strip any prompt injection attempts) |
| Scope limitation | Request minimal OAuth scopes (drive.readonly, repo read) |
| Token rotation | Google tokens auto-refresh; GitHub tokens are long-lived but revocable |
| Rate limiting | MCP tool calls count toward the per-user rate limit on `POST /api/chat` |

---

## 9. Testing Strategy

### 9.1 Unit Tests

Mock the MCP client session to test tool loading and conversion:

```python
async def test_tool_loading_with_no_connections():
    tools = await get_tools_for_user("user-with-no-connections")
    assert len(tools) == 3  # tavily, rag, store_memory

async def test_tool_loading_with_google():
    tools = await get_tools_for_user("user-with-google")
    tool_names = [t.name for t in tools]
    assert "search_files" in tool_names
    assert "read_file" in tool_names
```

### 9.2 Integration Tests

Test full flow with mock MCP server:

```python
async def test_agent_uses_gdrive_tool():
    # Start a mock MCP server that returns canned responses
    # Connect agent with mock Google token
    # Send a message like "Find my project proposal in Google Drive"
    # Assert agent calls search_files tool
    # Assert response references the file
```

### 9.3 Manual Testing

1. Connect Google Drive OAuth in settings
2. Ask SAM: "Search my Google Drive for recent documents"
3. Verify: tool_start/tool_end SSE events fire, results appear in response
4. Disconnect Google Drive
5. Ask same question — verify SAM explains Drive is not connected
