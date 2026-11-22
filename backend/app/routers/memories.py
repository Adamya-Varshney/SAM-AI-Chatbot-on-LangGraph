from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import CurrentUser, get_current_user
from app.database import get_connection

router = APIRouter(prefix="/api/memories", tags=["memories"])


@router.get("")
async def list_memories(
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    async with get_connection() as conn:
        if category:
            rows = await conn.fetch(
                """
                SELECT id, content, category, created_at
                FROM user_memories
                WHERE user_id = $1 AND category = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                """,
                user.user_id, category, limit, offset,
            )
            total = await conn.fetchval(
                "SELECT count(*) FROM user_memories WHERE user_id = $1 AND category = $2",
                user.user_id, category,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, content, category, created_at
                FROM user_memories
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                user.user_id, limit, offset,
            )
            total = await conn.fetchval(
                "SELECT count(*) FROM user_memories WHERE user_id = $1",
                user.user_id,
            )

    return {
        "memories": [
            {
                "id": str(r["id"]),
                "content": r["content"],
                "category": r["category"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    async with get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM user_memories WHERE id = $1 AND user_id = $2",
            memory_id, user.user_id,
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Memory not found")

    return {"id": memory_id, "deleted": True}
