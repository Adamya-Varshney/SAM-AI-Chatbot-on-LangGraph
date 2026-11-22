import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.auth import CurrentUser, get_current_user
from app.models import ChatRequest, TitleRequest
from app.database import get_connection
from app.services.agent import run_agent_stream, generate_title

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("")
async def chat(
    request: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
):
    async with get_connection() as conn:
        existing = await conn.fetchval(
            "SELECT thread_id FROM thread_metadata WHERE thread_id = $1 AND user_id = $2",
            request.thread_id, user.user_id,
        )
        if not existing:
            await conn.execute(
                "INSERT INTO thread_metadata (thread_id, user_id) VALUES ($1, $2)",
                request.thread_id, user.user_id,
            )

    async def event_stream():
        title_generated = False
        try:
            async for event_type, data in run_agent_stream(
                user_id=user.user_id,
                thread_id=request.thread_id,
                message=request.message,
                location=request.location,
                timezone=request.timezone,
            ):
                yield sse_event(event_type, data)

            # Auto-generate title on first message
            async with get_connection() as conn:
                row = await conn.fetchrow(
                    "SELECT title FROM thread_metadata WHERE thread_id = $1",
                    request.thread_id,
                )
                if row and row["title"] == "New Chat":
                    title = await generate_title(request.message)
                    await conn.execute(
                        "UPDATE thread_metadata SET title = $1 WHERE thread_id = $2",
                        title, request.thread_id,
                    )
                    title_generated = True

            yield sse_event("done", {
                "thread_id": request.thread_id,
                "title": title if title_generated else (row["title"] if row else "New Chat"),
                "title_generated": title_generated,
            })
        except Exception as e:
            logger.exception("Chat stream error")
            yield sse_event("error", {
                "code": "LLM_ERROR",
                "message": str(e),
            })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/title")
async def regenerate_title(
    request: TitleRequest,
    user: CurrentUser = Depends(get_current_user),
):
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT thread_id FROM thread_metadata WHERE thread_id = $1 AND user_id = $2",
            request.thread_id, user.user_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Thread not found")

    # Get first user message from checkpoints to regenerate title
    title = await generate_title(request.thread_id)

    async with get_connection() as conn:
        await conn.execute(
            "UPDATE thread_metadata SET title = $1 WHERE thread_id = $2",
            title, request.thread_id,
        )

    return {"thread_id": request.thread_id, "title": title}
