# SAM AI Chatbot v2 — Memory System Spec

**Version:** 1.0
**Date:** 2026-11-21
**Parent:** [01-PRD.md](./01-PRD.md)

---

## 1. Overview

SAM AI has two layers of memory:

1. **Conversation memory** (per-thread) — LangGraph checkpoints. Stores the full message history and agent state for each conversation thread. Already exists in v1 (SqliteSaver), migrated to `langgraph-checkpoint-postgres` in v2.

2. **Long-term memory** (per-user, cross-conversation) — New in v2. Facts, preferences, and context extracted from conversations, stored with vector embeddings for semantic recall. Persists across all threads.

```
┌─────────────────────────────────────────────┐
│              User "Adamya"                  │
│                                             │
│  Thread 1        Thread 2        Thread 3   │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐│
│  │checkpoint│   │checkpoint│   │checkpoint││
│  │checkpoint│   │checkpoint│   │          ││
│  │checkpoint│   │          │   │          ││
│  └──────────┘   └──────────┘   └──────────┘│
│                                             │
│  Long-term Memory (shared across threads)   │
│  ┌─────────────────────────────────────────┐│
│  │ "User is based in Noida, India"         ││
│  │ "User prefers Python over JavaScript"   ││
│  │ "User is building a chatbot project"    ││
│  │ "User works at <company>"               ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

---

## 2. Conversation Memory (LangGraph Checkpoints)

### 2.1 How It Works

LangGraph automatically checkpoints the full graph state after every node execution. This means every user message, assistant response, and tool call is persisted.

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpointer = AsyncPostgresSaver.from_conn_string(SUPABASE_DB_URL)
await checkpointer.setup()

graph = workflow.compile(checkpointer=checkpointer)
```

### 2.2 Thread Isolation

Each conversation is a separate thread identified by `thread_id`:

```python
config = {"configurable": {"thread_id": thread_id}}
result = await graph.ainvoke(state, config)
```

The checkpointer stores state keyed by `(thread_id, checkpoint_id)`. When a user opens an existing thread, LangGraph loads the latest checkpoint for that thread and the full message history is restored.

### 2.3 What's Stored in Checkpoints

| Data | Stored? | Notes |
|------|---------|-------|
| User messages | Yes | Full text |
| Assistant responses | Yes | Full text including markdown |
| Tool calls | Yes | Tool name, input, output |
| Tool results | Yes | Search results, RAG chunks |
| Agent state | Yes | Current node, pending actions |

### 2.4 Migration from v1

v1 uses `langgraph-checkpoint-sqlite` with a local SQLite file. Migration:

```python
# One-time migration script
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

sqlite_saver = SqliteSaver.from_conn_string("checkpoints.db")
postgres_saver = AsyncPostgresSaver.from_conn_string(SUPABASE_DB_URL)

# SqliteSaver and PostgresSaver use the same serialization format
# Export from SQLite, import to PostgreSQL
for thread_id in get_all_thread_ids(sqlite_saver):
    checkpoints = list(sqlite_saver.list({"configurable": {"thread_id": thread_id}}))
    for cp in checkpoints:
        await postgres_saver.aput(cp.config, cp.values, cp.metadata, cp.parent_config)
```

Since v1 has no authentication, migrated threads have no `user_id`. The migration assigns them to a designated legacy user, or they can be discarded since v1 runs on Streamlit Cloud where data is ephemeral.

---

## 3. Long-Term Memory

### 3.1 Architecture

Long-term memory operates on a **store-and-recall** pattern:

```
                    ┌──────────────────┐
                    │  During Chat     │
                    │                  │
  User message ───> │  1. RECALL       │ ──> relevant memories injected
                    │     (before LLM) │     into system prompt
                    │                  │
                    │  2. GENERATE     │ ──> LLM responds with
                    │     (LLM call)   │     memory context
                    │                  │
  LLM response ──> │  3. STORE        │ ──> new facts extracted
                    │     (after LLM)  │     and saved
                    └──────────────────┘
```

### 3.2 Memory Recall (Before LLM Call)

Before every LLM invocation, the backend:

1. Embeds the user's latest message using `text-embedding-3-small`
2. Queries `user_memories` for the top 5 most similar memories
3. Injects them into the system prompt

```python
async def recall_memories(user_id: str, query: str, limit: int = 5) -> list[str]:
    embedding = await embed_text(query)
    
    rows = await db.fetch(
        """
        SELECT content, category,
               1 - (embedding <=> $1::vector) AS similarity
        FROM user_memories
        WHERE user_id = $2
        ORDER BY embedding <=> $1::vector
        LIMIT $3
        """,
        embedding, user_id, limit,
    )
    
    return [
        row["content"] for row in rows
        if row["similarity"] > 0.3  # minimum relevance threshold
    ]
```

**System prompt injection:**

```python
memories = await recall_memories(user_id, user_message)

system_prompt = BASE_SYSTEM_PROMPT
if memories:
    memory_text = "\n".join(f"- {m}" for m in memories)
    system_prompt += f"""

You have the following knowledge about this user from previous conversations:
{memory_text}

Use this context naturally in your responses when relevant. Do not explicitly
mention that you "remember" things unless the user asks about your memory."""
```

### 3.3 Memory Storage (After LLM Response)

After each assistant response, a lightweight extraction step identifies storable facts:

```python
MEMORY_EXTRACTION_PROMPT = """Analyze this conversation exchange and extract any new facts about the user that would be useful to remember across future conversations.

User message: {user_message}
Assistant response: {assistant_response}

Extract facts in these categories:
- general: name, age, occupation
- preference: likes, dislikes, preferred tools/languages
- project: what they're working on, tech stack
- technical: skills, experience level
- personal: location, timezone, interests

Return a JSON array of objects with "content" and "category" fields.
Return an empty array if there are no new facts worth storing.

Rules:
- Only store facts explicitly stated or strongly implied by the user
- Do not store trivial facts (greetings, single-word responses)
- Do not store opinions the assistant expressed
- Keep each fact to one concise sentence"""
```

```python
async def extract_and_store_memories(
    user_id: str,
    user_message: str,
    assistant_response: str,
) -> list[dict]:
    extraction = await llm.ainvoke([
        SystemMessage(content=MEMORY_EXTRACTION_PROMPT.format(
            user_message=user_message,
            assistant_response=assistant_response,
        ))
    ])
    
    new_facts = parse_json(extraction.content)
    stored = []
    
    for fact in new_facts:
        # Check for duplicates using semantic similarity
        if await is_duplicate_memory(user_id, fact["content"]):
            continue
        
        embedding = await embed_text(fact["content"])
        
        await db.execute(
            """
            INSERT INTO user_memories (user_id, content, category, embedding)
            VALUES ($1, $2, $3, $4)
            """,
            user_id, fact["content"], fact["category"], embedding,
        )
        stored.append(fact)
    
    return stored
```

### 3.4 Duplicate Detection

Before storing a new memory, check if a semantically similar one already exists:

```python
async def is_duplicate_memory(user_id: str, content: str, threshold: float = 0.9) -> bool:
    embedding = await embed_text(content)
    
    row = await db.fetchrow(
        """
        SELECT 1 - (embedding <=> $1::vector) AS similarity
        FROM user_memories
        WHERE user_id = $2
        ORDER BY embedding <=> $1::vector
        LIMIT 1
        """,
        embedding, user_id,
    )
    
    return row is not None and row["similarity"] > threshold
```

If similarity > 0.9, the new fact is considered a duplicate and not stored. If similarity is between 0.7 and 0.9, the new fact may be an update — in that case, update the existing memory's content and re-embed.

### 3.5 Memory Categories

| Category | Examples | Typical source |
|----------|----------|---------------|
| `general` | "User's name is Adamya", "User is 26 years old" | Self-introduction |
| `preference` | "User prefers dark mode", "User likes Python over JS" | Stated preferences |
| `project` | "User is building a chatbot with LangGraph" | Project discussions |
| `technical` | "User is experienced with React and Next.js" | Technical conversations |
| `personal` | "User is based in Noida, India" | Location mentions, interests |

### 3.6 SSE Memory Event

When a memory is stored during a chat, the backend sends an SSE event so the frontend can show feedback:

```
event: memory_stored
data: {"content": "User is building a chatbot with LangGraph"}
```

The frontend shows a subtle toast or inline indicator: "Remembered: User is building a chatbot with LangGraph"

---

## 4. Memory in the LangGraph Agent

### 4.1 Integration Point

Memory recall and storage happen outside the core agent loop:

```python
async def handle_chat(user_id: str, thread_id: str, message: str):
    # 1. Recall relevant memories
    memories = await recall_memories(user_id, message)
    
    # 2. Build state with memory-augmented system prompt
    state = {
        "messages": [
            SystemMessage(content=build_system_prompt(memories)),
            HumanMessage(content=message),
        ]
    }
    
    # 3. Run LangGraph agent (chat_node <-> tools loop)
    config = {"configurable": {"thread_id": thread_id}}
    async for event in graph.astream_events(state, config, version="v2"):
        yield format_sse_event(event)
    
    # 4. Extract and store new memories (async, doesn't block response)
    assistant_response = get_last_assistant_message(thread_id)
    stored = await extract_and_store_memories(user_id, message, assistant_response)
    
    for memory in stored:
        yield format_sse_event("memory_stored", memory)
```

### 4.2 Memory Tool (Optional Enhancement)

The agent can also have an explicit `store_memory` tool for when users say things like "Remember that I prefer tabs over spaces":

```python
@tool
async def store_memory(fact: str, category: str = "general") -> str:
    """Store a fact about the user for future conversations.
    
    Use this when the user explicitly asks you to remember something,
    or when they share an important personal detail.
    
    Args:
        fact: The fact to remember, as a concise sentence.
        category: One of: general, preference, project, technical, personal.
    """
    embedding = await embed_text(fact)
    await db.execute(
        "INSERT INTO user_memories (user_id, content, category, embedding) VALUES ($1, $2, $3, $4)",
        current_user_id, fact, category, embedding,
    )
    return f"I'll remember that: {fact}"
```

---

## 5. Memory Management (User-Facing)

### 5.1 View Memories

Users can see all stored memories on the Settings page:

```
GET /api/memories?limit=50&offset=0
```

Memories displayed grouped by category, newest first. Each memory shows content, category badge, and creation date.

### 5.2 Delete Memories

Users can delete individual memories:

```
DELETE /api/memories/{memory_id}
```

This removes the memory row and its embedding from the database. The memory will no longer be recalled in future conversations.

### 5.3 No Edit

Users cannot edit memory content (the embedding would need to be regenerated). To correct a memory, delete the wrong one and tell SAM the correct fact in a conversation — it will be stored automatically.

---

## 6. Performance Considerations

| Operation | Latency (est.) | Strategy |
|-----------|---------------|----------|
| Embed user message | ~100ms | Single API call to OpenAI |
| Recall memories (vector search) | ~20ms | pgvector IVFFlat index |
| Memory extraction (LLM call) | ~500ms | GPT-4o-mini, runs async after response |
| Duplicate check (vector search) | ~20ms | Same index as recall |
| Store memory (INSERT) | ~5ms | Single row insert |

**Key optimization:** Memory extraction runs asynchronously after the response stream completes. It does not add latency to the user-visible response. The `memory_stored` SSE events are sent after the `done` event.

---

## 7. Embedding Model

| Attribute | Value |
|-----------|-------|
| Model | `text-embedding-3-small` |
| Dimensions | 1536 |
| Max tokens | 8191 |
| Cost | $0.02 per 1M tokens |

**Why text-embedding-3-small:**
- Low cost (20x cheaper than text-embedding-3-large)
- Good quality for short text similarity (memories are 1-2 sentences)
- 1536 dimensions is the standard pgvector column size
- Same model used for RAG document chunks, keeping one embedding model across the system

---

## 8. Limits and Constraints

| Constraint | Value | Rationale |
|-----------|-------|-----------|
| Max memories per user | 500 | Storage + recall quality (too many memories dilute results) |
| Max memory content length | 500 chars | Keeps embeddings meaningful |
| Recall results per query | 5 | Sufficient context without overloading the system prompt |
| Minimum recall similarity | 0.3 | Below this, memories are irrelevant noise |
| Duplicate threshold | 0.9 | High bar to avoid near-duplicates |
| Extraction rate | Max 3 facts per exchange | Prevents over-extraction from long conversations |
