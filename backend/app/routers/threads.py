from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import CurrentUser, get_current_user
from app.models import ThreadRenameRequest
from app.database import get_connection

router = APIRouter(prefix="/api/threads", tags=["threads"])


@router.get("")
async def list_threads(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    async with get_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT t.thread_id, t.title, t.created_at, t.updated_at,
                   EXISTS(SELECT 1 FROM document_metadata d WHERE d.thread_id = t.thread_id AND d.user_id = $1) AS has_document
            FROM thread_metadata t
            WHERE t.user_id = $1
            ORDER BY t.updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            user.user_id, limit, offset,
        )
        total = await conn.fetchval(
            "SELECT count(*) FROM thread_metadata WHERE user_id = $1",
            user.user_id,
        )

    return {
        "threads": [
            {
                "thread_id": r["thread_id"],
                "title": r["title"],
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
                "has_document": r["has_document"],
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{thread_id}")
async def get_thread(
    thread_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT thread_id, title, created_at FROM thread_metadata WHERE thread_id = $1 AND user_id = $2",
            thread_id, user.user_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Thread not found")

        doc = await conn.fetchrow(
            "SELECT filename, page_count, chunk_count, created_at FROM document_metadata WHERE thread_id = $1 AND user_id = $2 LIMIT 1",
            thread_id, user.user_id,
        )

    # Messages are loaded from LangGraph checkpoints
    from app.services.agent import get_thread_messages
    messages = await get_thread_messages(thread_id)

    result = {
        "thread_id": row["thread_id"],
        "title": row["title"],
        "created_at": row["created_at"].isoformat(),
        "messages": messages,
    }

    if doc:
        result["document"] = {
            "filename": doc["filename"],
            "page_count": doc["page_count"],
            "chunk_count": doc["chunk_count"],
            "uploaded_at": doc["created_at"].isoformat(),
        }

    return result


@router.patch("/{thread_id}")
async def rename_thread(
    thread_id: str,
    body: ThreadRenameRequest,
    user: CurrentUser = Depends(get_current_user),
):
    async with get_connection() as conn:
        result = await conn.execute(
            "UPDATE thread_metadata SET title = $1 WHERE thread_id = $2 AND user_id = $3",
            body.title, thread_id, user.user_id,
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Thread not found")

    return {"thread_id": thread_id, "title": body.title}


@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    async with get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM thread_metadata WHERE thread_id = $1 AND user_id = $2",
            thread_id, user.user_id,
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Thread not found")

        await conn.execute(
            "DELETE FROM document_chunks WHERE thread_id = $1 AND user_id = $2",
            thread_id, user.user_id,
        )
        await conn.execute(
            "DELETE FROM document_metadata WHERE thread_id = $1 AND user_id = $2",
            thread_id, user.user_id,
        )

    return {"thread_id": thread_id, "deleted": True}
