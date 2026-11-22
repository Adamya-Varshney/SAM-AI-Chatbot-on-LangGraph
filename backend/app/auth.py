from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
from app.config import Settings, get_settings


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
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
