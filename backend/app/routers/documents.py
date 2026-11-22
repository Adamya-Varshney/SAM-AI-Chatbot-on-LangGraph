from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.auth import CurrentUser, get_current_user
from app.database import get_connection
from app.services.documents import ingest_pdf

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    thread_id: str = Form(...),
    user: CurrentUser = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 20MB)")

    async with get_connection() as conn:
        existing = await conn.fetchval(
            "SELECT id FROM document_metadata WHERE user_id = $1 AND thread_id = $2 AND filename = $3",
            user.user_id, thread_id, file.filename,
        )
        if existing:
            raise HTTPException(status_code=409, detail="This PDF is already ingested for this thread")

    result = await ingest_pdf(
        user_id=user.user_id,
        thread_id=thread_id,
        filename=file.filename,
        content=content,
    )

    return {
        "filename": file.filename,
        "thread_id": thread_id,
        "page_count": result["page_count"],
        "chunk_count": result["chunk_count"],
        "file_size": len(content),
    }


@router.get("/{thread_id}")
async def list_documents(
    thread_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT id, filename, page_count, chunk_count, file_size, created_at
            FROM document_metadata
            WHERE user_id = $1 AND thread_id = $2
            ORDER BY created_at DESC
            """,
            user.user_id, thread_id,
        )

    return {
        "documents": [
            {
                "id": str(r["id"]),
                "filename": r["filename"],
                "page_count": r["page_count"],
                "chunk_count": r["chunk_count"],
                "file_size": r["file_size"],
                "uploaded_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    async with get_connection() as conn:
        doc = await conn.fetchrow(
            "SELECT id, thread_id FROM document_metadata WHERE id = $1 AND user_id = $2",
            document_id, user.user_id,
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        await conn.execute(
            "DELETE FROM document_chunks WHERE user_id = $1 AND thread_id = $2",
            user.user_id, doc["thread_id"],
        )
        await conn.execute(
            "DELETE FROM document_metadata WHERE id = $1",
            document_id,
        )

    return {"id": document_id, "deleted": True}
