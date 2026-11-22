import logging
import httpx
from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError, jwk
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_jwks_cache: dict | None = None


async def _get_jwks(supabase_url: str) -> dict:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def _find_key(jwks: dict, kid: str) -> dict | None:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


class CurrentUser:
    def __init__(self, user_id: str, email: str | None, role: str):
        self.user_id = user_id
        self.email = email
        self.role = role


async def get_current_user(
    authorization: str = Header(...),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.removeprefix("Bearer ")
    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token header")

    alg = header.get("alg", "HS256")

    try:
        if alg == "ES256":
            kid = header.get("kid", "")
            jwks = await _get_jwks(settings.supabase_url)
            key_data = _find_key(jwks, kid)
            if not key_data:
                global _jwks_cache
                _jwks_cache = None
                jwks = await _get_jwks(settings.supabase_url)
                key_data = _find_key(jwks, kid)
            if not key_data:
                raise JWTError(f"No matching key found for kid={kid}")
            public_key = jwk.construct(key_data, algorithm="ES256")
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        else:
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )

        return CurrentUser(
            user_id=payload["sub"],
            email=payload.get("email"),
            role=payload.get("role", "authenticated"),
        )
    except JWTError as e:
        logger.error("JWT validation failed: alg=%s err=%s", alg, e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")
