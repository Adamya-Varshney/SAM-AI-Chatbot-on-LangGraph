import logging
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.auth import CurrentUser, get_current_user
from app.config import Settings, get_settings
from app.database import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

PROVIDERS = {"google", "github"}

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


def _get_fernet(settings: Settings) -> Fernet:
    if not settings.encryption_key:
        raise HTTPException(status_code=500, detail="Encryption key not configured")
    return Fernet(settings.encryption_key.encode())


def _redirect_uri(settings: Settings, provider: str) -> str:
    return f"{settings.backend_url.rstrip('/')}/api/auth/callback/{provider}"


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
            "redirect_uri": _redirect_uri(settings, "google"),
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/drive.readonly",
            "access_type": "offline",
            "prompt": "consent",
            "state": user.user_id,
        }
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
        return {"redirect_url": url}

    if provider == "github":
        if not settings.github_client_id:
            raise HTTPException(status_code=501, detail="GitHub OAuth not configured")
        params = {
            "client_id": settings.github_client_id,
            "redirect_uri": _redirect_uri(settings, "github"),
            "scope": "repo read:user",
            "state": user.user_id,
        }
        url = "https://github.com/login/oauth/authorize?" + urlencode(params)
        return {"redirect_url": url}


@router.get("/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    settings: Settings = Depends(get_settings),
):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    user_id = state
    fernet = _get_fernet(settings)

    try:
        if provider == "google":
            async with httpx.AsyncClient() as client:
                resp = await client.post(GOOGLE_TOKEN_URL, data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": _redirect_uri(settings, "google"),
                    "grant_type": "authorization_code",
                })
            if resp.status_code != 200:
                logger.error("Google token exchange failed: %s", resp.text)
                return RedirectResponse(f"{settings.frontend_url}/settings?error=token_exchange_failed")
            tokens = resp.json()
            access_token = tokens["access_token"]
            refresh_token = tokens.get("refresh_token")
            scopes = tokens.get("scope", "").split()

        elif provider == "github":
            async with httpx.AsyncClient() as client:
                resp = await client.post(GITHUB_TOKEN_URL, data={
                    "code": code,
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "redirect_uri": _redirect_uri(settings, "github"),
                }, headers={"Accept": "application/json"})
            if resp.status_code != 200:
                logger.error("GitHub token exchange failed: %s", resp.text)
                return RedirectResponse(f"{settings.frontend_url}/settings?error=token_exchange_failed")
            tokens = resp.json()
            if "error" in tokens:
                logger.error("GitHub token error: %s", tokens)
                return RedirectResponse(f"{settings.frontend_url}/settings?error=token_exchange_failed")
            access_token = tokens["access_token"]
            refresh_token = None
            scopes = tokens.get("scope", "").split(",")

        encrypted_access = fernet.encrypt(access_token.encode()).decode()
        encrypted_refresh = fernet.encrypt(refresh_token.encode()).decode() if refresh_token else None

        async with get_connection() as conn:
            await conn.execute(
                """
                INSERT INTO user_oauth_tokens (user_id, provider, access_token, refresh_token, scopes)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, provider)
                DO UPDATE SET access_token = $3, refresh_token = $4, scopes = $5, updated_at = now()
                """,
                user_id, provider, encrypted_access, encrypted_refresh, scopes,
            )

        return RedirectResponse(f"{settings.frontend_url}/settings?connected={provider}")

    except Exception:
        logger.exception("OAuth callback failed for %s", provider)
        return RedirectResponse(f"{settings.frontend_url}/settings?error=callback_failed")


@router.delete("/disconnect/{provider}")
async def disconnect_provider(
    provider: str,
    user: CurrentUser = Depends(get_current_user),
):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    async with get_connection() as conn:
        await conn.execute(
            "DELETE FROM user_oauth_tokens WHERE user_id = $1 AND provider = $2",
            user.user_id, provider,
        )

    return {"provider": provider, "disconnected": True}
