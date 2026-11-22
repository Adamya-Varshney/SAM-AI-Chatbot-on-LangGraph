from datetime import datetime, timezone
from fastapi import APIRouter
from app.database import get_pool

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check():
    db_status = "connected"
    try:
        async with get_pool().acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "version": "2.0.0",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
