import logging
from io import BytesIO
from pypdf import PdfReader

from app.database import get_connection
from app.services.memory import embed_text

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def extract_pages(content: bytes) -> list[tuple[int, str]]:
    reader = PdfReader(BytesIO(content))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((i + 1, text))
    return pages


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


async def ingest_pdf(
    user_id: str,
    thread_id: str,
    filename: str,
    content: bytes,
) -> dict:
    pages = extract_pages(content)
    page_count = len(pages)

    all_chunks = []
    for page_num, page_text in pages:
        chunks = chunk_text(page_text)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "page_number": page_num,
                "chunk_index": len(all_chunks),
                "content": chunk,
            })

    async with get_connection() as conn:
        for chunk in all_chunks:
            embedding = await embed_text(chunk["content"])
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            await conn.execute(
                """
                INSERT INTO document_chunks (user_id, thread_id, filename, page_number, chunk_index, content, embedding)
                VALUES ($1, $2, $3, $4, $5, $6, $7::vector)
                """,
                user_id, thread_id, filename,
                chunk["page_number"], chunk["chunk_index"],
                chunk["content"], embedding_str,
            )

        await conn.execute(
            """
            INSERT INTO document_metadata (user_id, thread_id, filename, page_count, chunk_count, file_size)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user_id, thread_id, filename, page_count, len(all_chunks), len(content),
        )

    return {"page_count": page_count, "chunk_count": len(all_chunks)}
