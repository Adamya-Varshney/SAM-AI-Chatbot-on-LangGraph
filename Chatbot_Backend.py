from __future__ import annotations

import os
import sqlite3
import tempfile
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from pathlib import Path

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.vectorstores import FAISS
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

if not os.getenv("OPENAI_API_KEY"):
    try:
        import streamlit as st
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

# ---------------------------------------------------------------------------
# LLM + Embeddings
# ---------------------------------------------------------------------------
llm = ChatOpenAI(model="gpt-4o-mini")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# ---------------------------------------------------------------------------
# Per-thread PDF retriever store
# ---------------------------------------------------------------------------
_THREAD_RETRIEVERS: Dict[str, Any] = {}
_THREAD_METADATA: Dict[str, dict] = {}


def _get_retriever(thread_id: Optional[str]):
    if thread_id and thread_id in _THREAD_RETRIEVERS:
        return _THREAD_RETRIEVERS[thread_id]
    return None


def ingest_pdf(file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
    if not file_bytes:
        raise ValueError("No bytes received for ingestion.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        temp_path = tmp.name

    try:
        loader = PyPDFLoader(temp_path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(docs)

        vector_store = FAISS.from_documents(chunks, embeddings)
        retriever = vector_store.as_retriever(
            search_type="similarity", search_kwargs={"k": 4}
        )

        tid = str(thread_id)
        _THREAD_RETRIEVERS[tid] = retriever
        _THREAD_METADATA[tid] = {
            "filename": filename or os.path.basename(temp_path),
            "documents": len(docs),
            "chunks": len(chunks),
        }
        return _THREAD_METADATA[tid]
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def thread_has_document(thread_id: str) -> bool:
    return str(thread_id) in _THREAD_RETRIEVERS


def thread_document_metadata(thread_id: str) -> dict:
    return _THREAD_METADATA.get(str(thread_id), {})


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
search_tool = DuckDuckGoSearchRun(region="us-en")


@tool
def rag_tool(query: str, thread_id: Optional[str] = None) -> dict:
    """Retrieve relevant information from the uploaded PDF for this chat thread.
    Always include the thread_id when calling this tool."""
    retriever = _get_retriever(thread_id)
    if retriever is None:
        return {
            "error": "No document indexed for this chat. Upload a PDF first.",
            "query": query,
        }

    result = retriever.invoke(query)
    context = [doc.page_content for doc in result]
    metadata = [doc.metadata for doc in result]

    return {
        "query": query,
        "context": context,
        "metadata": metadata,
        "source_file": _THREAD_METADATA.get(str(thread_id), {}).get("filename"),
    }


tools = [search_tool, rag_tool]
llm_with_tools = llm.bind_tools(tools)

# ---------------------------------------------------------------------------
# Title generation (unchanged)
# ---------------------------------------------------------------------------
def generate_title(user_msg: str, ai_msg: str) -> str:
    prompt = [
        SystemMessage(content=(
            "You create very short titles for chat conversations. "
            "Given the first user message and the assistant's reply, return a concise "
            "title of at most 5 words capturing the topic. Return ONLY the title text — "
            "no quotes, no trailing punctuation, no preamble."
        )),
        HumanMessage(content=f"User: {user_msg}\n\nAssistant: {ai_msg[:1000]}"),
    ]
    result = llm.invoke(prompt)
    title = result.content.strip().strip('"').strip()
    return title or "New Chat"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are SAM, a helpful multi-utility AI assistant. You have the following capabilities:\n"
    "\n"
    "1. **PDF Q&A (RAG)**: When a PDF has been uploaded, use the `rag_tool` (always pass "
    "the thread_id `{thread_id}`) to retrieve relevant passages before answering. "
    "If no document is available and the user asks about one, ask them to upload a PDF.\n"
    "\n"
    "2. **Web Search**: Use the `duckduckgo_search` tool to look up current information, "
    "recent events, or anything not in your training data.\n"
    "\n"
    "3. **Code Interpreter**: You can write, explain, debug, and execute Python code. "
    "When the user asks you to run code, write the code in a fenced ```python block, "
    "walk through its execution step by step, and provide the final output. "
    "For calculations, data transformations, or algorithmic questions, prefer writing "
    "and tracing code over prose explanations.\n"
)


def chat_node(state: ChatState, config=None):
    cfg = config.get("configurable", {}) if config else {}
    thread_id = cfg.get("thread_id")
    location = cfg.get("user_location")
    timezone = cfg.get("user_timezone")
    local_time = cfg.get("local_time")

    context_bits = []
    if location:
        context_bits.append(f"The user's location is {location}.")
    if timezone:
        context_bits.append(f"The user's time zone is {timezone}.")
    if local_time:
        context_bits.append(f"The user's current local date and time is {local_time}.")

    has_doc = thread_has_document(thread_id) if thread_id else False
    if has_doc:
        meta = thread_document_metadata(thread_id)
        context_bits.append(
            f"A PDF is indexed for this chat: \"{meta.get('filename')}\" "
            f"({meta.get('chunks')} chunks, {meta.get('documents')} pages)."
        )

    system_text = SYSTEM_PROMPT.format(thread_id=thread_id or "unknown")
    if context_bits:
        system_text += "\nUser context: " + " ".join(context_bits)

    system_msg = SystemMessage(content=system_text)
    messages = [system_msg, *state["messages"]]
    response = llm_with_tools.invoke(messages, config=config)
    return {"messages": [response]}


tool_node = ToolNode(tools)

# ---------------------------------------------------------------------------
# SQLite persistence
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent / "sam_memory.db"

_checkpoint_conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
checkpointer = SqliteSaver(_checkpoint_conn)
checkpointer.setup()

_meta_conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
_meta_conn.execute("""
    CREATE TABLE IF NOT EXISTS thread_metadata (
        thread_id TEXT PRIMARY KEY,
        title     TEXT NOT NULL DEFAULT 'New Chat',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
_meta_conn.commit()


def save_thread_title(thread_id: str, title: str) -> None:
    _meta_conn.execute(
        "INSERT INTO thread_metadata (thread_id, title) VALUES (?, ?) "
        "ON CONFLICT(thread_id) DO UPDATE SET title = excluded.title",
        (str(thread_id), title),
    )
    _meta_conn.commit()


def get_thread_title(thread_id: str) -> str:
    row = _meta_conn.execute(
        "SELECT title FROM thread_metadata WHERE thread_id = ?",
        (str(thread_id),),
    ).fetchone()
    return row[0] if row else "New Chat"


def list_all_threads() -> List[dict]:
    rows = _meta_conn.execute(
        "SELECT thread_id, title FROM thread_metadata ORDER BY created_at ASC"
    ).fetchall()
    return [{"thread_id": r[0], "title": r[1]} for r in rows]


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")
graph.add_conditional_edges("chat_node", tools_condition)
graph.add_edge("tools", "chat_node")

chatbot = graph.compile(checkpointer=checkpointer)
