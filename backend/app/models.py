from pydantic import BaseModel, Field
from datetime import datetime


class ChatRequest(BaseModel):
    thread_id: str
    message: str = Field(min_length=1, max_length=10000)
    location: str | None = Field(default=None, max_length=200)
    timezone: str | None = None


class TitleRequest(BaseModel):
    thread_id: str


class TitleResponse(BaseModel):
    thread_id: str
    title: str


class ThreadSummary(BaseModel):
    thread_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    has_document: bool = False


class ThreadListResponse(BaseModel):
    threads: list[ThreadSummary]
    total: int
    limit: int
    offset: int


class MessageOut(BaseModel):
    role: str
    content: str
    timestamp: datetime
    tools_used: list[str] = []


class DocumentInfo(BaseModel):
    filename: str
    page_count: int
    chunk_count: int
    uploaded_at: datetime


class ThreadDetailResponse(BaseModel):
    thread_id: str
    title: str
    created_at: datetime
    messages: list[MessageOut]
    document: DocumentInfo | None = None


class ThreadRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class DocumentUploadResponse(BaseModel):
    filename: str
    thread_id: str
    page_count: int
    chunk_count: int
    file_size: int


class DocumentListItem(BaseModel):
    id: str
    filename: str
    page_count: int
    chunk_count: int
    file_size: int | None
    uploaded_at: datetime


class MemoryItem(BaseModel):
    id: str
    content: str
    category: str
    created_at: datetime


class MemoryListResponse(BaseModel):
    memories: list[MemoryItem]
    total: int
    limit: int
    offset: int


class ConnectionInfo(BaseModel):
    provider: str
    connected: bool
    scopes: list[str]
    connected_at: datetime | None


class ErrorResponse(BaseModel):
    error: dict


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    timestamp: datetime
