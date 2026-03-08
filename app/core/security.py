from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from app.core.config import settings


def create_access_token(user_id: int, expire_minutes: Optional[int] = None) -> str:
    if expire_minutes is None:
        expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expire_minutes)
    payload = {
        "sub": str(user_id),
        "user_id": user_id,
        "type": "access",
        "iss": settings.PROJECT_NAME,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.PROJECT_NAME,
        )
        return payload
    except jwt.PyJWTError:
        return None
