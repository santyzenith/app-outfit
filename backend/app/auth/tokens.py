import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "typ": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    # Raises jwt.PyJWTError or ValueError when the token is not a valid access token.
    payload = jwt.decode(
        token,
        get_settings().jwt_secret,
        algorithms=[ALGORITHM],
        options={"require": ["exp", "sub"]},
    )
    if payload.get("typ") != ACCESS_TOKEN_TYPE:
        raise ValueError("not an access token")
    return uuid.UUID(payload["sub"])


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    # Only the hash is stored, so a database leak does not expose usable tokens.
    return hashlib.sha256(raw_token.encode()).hexdigest()
