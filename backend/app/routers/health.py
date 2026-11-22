import base64
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Header
from jose import jwt, JWTError
from app.config import get_settings
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


@router.get("/debug/jwt")
async def debug_jwt(authorization: str = Header(default="")):
    """Temporary diagnostic endpoint — remove after fixing 401s."""
    settings = get_settings()
    secret = settings.supabase_jwt_secret

    result: dict = {
        "secret_len": len(secret),
        "secret_first4": secret[:4] if len(secret) >= 4 else "***",
        "secret_last4": secret[-4:] if len(secret) >= 4 else "***",
        "secret_has_whitespace": secret != secret.strip(),
    }

    if not authorization.startswith("Bearer "):
        result["error"] = "No Bearer token provided. Pass Authorization: Bearer <token>"
        return result

    token = authorization.removeprefix("Bearer ")
    parts = token.split(".")
    result["token_parts"] = len(parts)

    if len(parts) >= 2:
        try:
            padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
            payload_raw = base64.urlsafe_b64decode(padded)
            payload = json.loads(payload_raw)
            result["token_payload"] = {
                "iss": payload.get("iss"),
                "aud": payload.get("aud"),
                "role": payload.get("role"),
                "sub": payload.get("sub", "")[:8] + "...",
                "exp": payload.get("exp"),
                "iat": payload.get("iat"),
            }
        except Exception as e:
            result["payload_decode_error"] = str(e)

    try:
        decoded = jwt.decode(
            token, secret, algorithms=["HS256"], audience="authenticated"
        )
        result["validation"] = "SUCCESS"
        result["decoded_sub"] = decoded.get("sub", "")[:8] + "..."
    except JWTError as e:
        result["validation"] = "FAILED"
        result["jwt_error"] = str(e)

        try:
            no_verify = jwt.decode(
                token, secret, algorithms=["HS256"],
                options={"verify_signature": False, "verify_aud": False, "verify_exp": False},
            )
            result["without_verification"] = {
                "aud": no_verify.get("aud"),
                "exp": no_verify.get("exp"),
                "role": no_verify.get("role"),
            }
        except Exception:
            pass

        try:
            jwt.decode(
                token, secret, algorithms=["HS256"],
                options={"verify_aud": False},
            )
            result["hint"] = "Signature OK but audience mismatch"
        except JWTError:
            try:
                jwt.decode(
                    token, secret, algorithms=["HS256"],
                    options={"verify_exp": False},
                    audience="authenticated",
                )
                result["hint"] = "Signature+audience OK but token expired"
            except JWTError:
                result["hint"] = "Signature verification failed — wrong JWT secret"

    return result
