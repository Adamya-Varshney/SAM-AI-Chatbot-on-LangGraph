import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import ToolNode

from app.config import get_settings
from app.services.memory import recall_memories, extract_and_store_memories, embed_text
from app.database import get_connection

logger = logging.getLogger(__name__)

BASE_SYSTEM_PROMPT = """You are SAM AI, an intelligent assistant built by Adamya Varshney. You are helpful, friendly, and knowledgeable.

You have access to tools that let you search the web, retrieve information from uploaded documents, and remember facts about the user across conversations.

Current context:
- Location: {location}
- Timezone: {timezone}
- Date: {date}

Guidelines:
- Use tools when the user's question requires up-to-date info or specific data.
- Be concise but thorough. Use markdown formatting for readability.
- If you use information from a web search, mention it naturally.
- If you remember something about the user, use it naturally without explicitly saying "I remember."
- When the user mentions uploading a file or their message indicates a file was uploaded (e.g. "[User uploaded file: ...]"), ALWAYS use the search_uploaded_documents tool to find and reference the document content before responding.
"""


def build_system_prompt(memories: list[str], location: str | None, timezone: str | None) -> str:
    from datetime import datetime, timezone as tz
    prompt = BASE_SYSTEM_PROMPT.format(
        location=location or "Unknown",
        timezone=timezone or "UTC",
        date=datetime.now(tz.utc).strftime("%Y-%m-%d"),
    )
    if memories:
        memory_text = "\n".join(f"- {m}" for m in memories)
        prompt += f"""
You have the following knowledge about this user from previous conversations:
{memory_text}

Use this context naturally in your responses when relevant."""
    return prompt


def _make_document_search_tool(user_id: str, thread_id: str):
    @tool
    async def search_uploaded_documents(query: str) -> str:
        """Search the user's uploaded PDF documents for relevant information. Use this when the user asks about content from a document or PDF they uploaded."""
        try:
            embedding = await embed_text(query)
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            async with get_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT content, filename, page_number,
                           1 - (embedding <=> $1::vector) AS similarity
                    FROM document_chunks
                    WHERE user_id = $2 AND thread_id = $3
                    ORDER BY embedding <=> $1::vector
                    LIMIT 5
                    """,
                    embedding_str, user_id, thread_id,
                )

            if not rows:
                return "No documents have been uploaded to this conversation yet."

            results = []
            for row in rows:
                if row["similarity"] > 0.3:
                    results.append(
                        f"[{row['filename']}, page {row['page_number']}]\n{row['content']}"
                    )

            if not results:
                return "No relevant content found in the uploaded documents."

            return "\n\n---\n\n".join(results)
        except Exception as e:
            logger.exception("Document search failed")
            return f"Error searching documents: {e}"

    return search_uploaded_documents


def get_tools(user_id: str | None = None, thread_id: str | None = None):
    from langchain_community.tools.tavily_search import TavilySearchResults
    settings = get_settings()
    tools = []
    if settings.tavily_api_key:
        tools.append(TavilySearchResults(max_results=3))
    if user_id and thread_id:
        tools.append(_make_document_search_tool(user_id, thread_id))
    return tools


@asynccontextmanager
async def get_checkpointer():
    settings = get_settings()
    async with AsyncPostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
        await checkpointer.setup()
        yield checkpointer


def build_graph(tools: list):
    llm = ChatOpenAI(model="gpt-4o-mini", streaming=True)

    if tools:
        llm_with_tools = llm.bind_tools(tools)
    else:
        llm_with_tools = llm

    async def chat_node(state: MessagesState):
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: MessagesState):
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    graph = StateGraph(MessagesState)
    graph.add_node("chat", chat_node)

    if tools:
        graph.add_node("tools", ToolNode(tools))
        graph.add_conditional_edges("chat", should_continue, {"tools": "tools", END: END})
        graph.add_edge("tools", "chat")
    else:
        graph.add_edge("chat", END)

    graph.add_edge(START, "chat")
    return graph


async def run_agent_stream(
    user_id: str,
    thread_id: str,
    message: str,
    location: str | None = None,
    timezone: str | None = None,
) -> AsyncGenerator[tuple[str, dict], None]:
    memories = await recall_memories(user_id, message)
    system_prompt = build_system_prompt(memories, location, timezone)

    tools = get_tools(user_id=user_id, thread_id=thread_id)
    graph = build_graph(tools)

    async with get_checkpointer() as checkpointer:
        compiled = graph.compile(checkpointer=checkpointer)

        state = {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message),
            ]
        }
        config = {"configurable": {"thread_id": thread_id}}

        collected_text = ""

        async for event in compiled.astream_events(state, config, version="v2"):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                    continue
                if hasattr(chunk, "content") and chunk.content and isinstance(chunk.content, str):
                    collected_text += chunk.content
                    yield ("token", {"content": chunk.content})

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                yield ("tool_start", {"tool": tool_name, "label": f"Using {tool_name}..."})

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                yield ("tool_end", {"tool": tool_name, "label": f"{tool_name} complete"})

    # Store memories asynchronously after response
    stored = await extract_and_store_memories(user_id, message, collected_text)
    for memory in stored:
        yield ("memory_stored", {"content": memory["content"]})


async def generate_title(text: str) -> str:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    response = await llm.ainvoke([
        SystemMessage(content="Generate a short title (max 6 words) for this conversation. Return only the title, no quotes."),
        HumanMessage(content=text),
    ])
    return response.content.strip()[:200]


async def get_thread_messages(thread_id: str) -> list[dict]:
    config = {"configurable": {"thread_id": thread_id}}

    try:
        async with get_checkpointer() as checkpointer:
            state = await checkpointer.aget(config)
            if not state or "channel_values" not in state:
                return []

            messages = state["channel_values"].get("messages", [])
            result = []
            for msg in messages:
                if isinstance(msg, SystemMessage):
                    continue
                result.append({
                    "role": "user" if isinstance(msg, HumanMessage) else "assistant",
                    "content": msg.content,
                    "timestamp": getattr(msg, "response_metadata", {}).get("timestamp", None),
                    "tools_used": [],
                })
            return result
    except Exception:
        logger.exception("Failed to load thread messages")
        return []
