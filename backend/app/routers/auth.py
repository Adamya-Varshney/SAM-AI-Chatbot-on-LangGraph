from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.auth import CurrentUser, get_current_user
from app.config import Settings, get_settings
from app.database import get_connection

router = APIRouter(prefix="/api/auth", tags=["auth"])

PROVIDERS = {"google", "github"}


@router.get("/me")
async def get_me(user: CurrentUser = Depends(get_current_user)):
    return {
        "id": user.user_id,
        "email": user.email,
    }


@router.get("/connections")
async def list_connections(user: CurrentUser = Depends(get_current_user)):
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT provider, scopes, created_at FROM user_oauth_tokens WHERE user_id = $1",
            user.user_id,
        )

    connected = {r["provider"]: r for r in rows}
    connections = []
    for provider in PROVIDERS:
        if provider in connected:
            row = connected[provider]
            connections.append({
                "provider": provider,
                "connected": True,
                "scopes": row["scopes"] or [],
                "connected_at": row["created_at"].isoformat(),
            })
        else:
            connections.append({
                "provider": provider,
                "connected": False,
                "scopes": [],
                "connected_at": None,
            })

    return {"connections": connections}


@router.get("/connect/{provider}")
async def connect_provider(
    provider: str,
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    if provider == "google":
        if not settings.google_client_id:
            raise HTTPException(status_code=501, detail="Google OAuth not configured")
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": f"{settings.supabase_url.rstrip('/')}/api/auth/callback/google",
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/drive.readonly",
            "access_type": "offline",
            "prompt": "consent",
            "state": user.user_id,
        }
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + "&".join(
            f"{k}={v}" for k, v in params.items()
        )
        return RedirectResponse(url)

    if provider == "github":
        if not settings.github_client_id:
            raise HTTPException(status_code=501, detail="GitHub OAuth not configured")
        params = {
            "client_id": settings.github_client_id,
            "redirect_uri": f"{settings.supabase_url.rstrip('/')}/api/auth/callback/github",
            "scope": "repo read:user",
            "state": user.user_id,
        }
        url = "https://github.com/login/oauth/authorize?" + "&".join(
            f"{k}={v}" for k, v in params.items()
        )
        return RedirectResponse(url)


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    settings: Settings = Depends(get_settings),
):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    # TODO: Exchange code for tokens, encrypt, store in user_oauth_tokens
    # For now, redirect back to frontend with status
    return RedirectResponse(f"{settings.frontend_url}/settings?connected={provider}")


@router.delete("/disconnect/{provider}")
async def disconnect_provider(
    provider: str,
    user: CurrentUser = Depends(get_current_user),
):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    async with get_connection() as conn:
        result = await conn.execute(
            "DELETE FROM user_oauth_tokens WHERE user_id = $1 AND provider = $2",
            user.user_id, provider,
        )

    return {"provider": provider, "disconnected": True}
