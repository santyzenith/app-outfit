from fastapi import APIRouter, HTTPException, Request, status

from app.api.schemas import IdTokenIn, RefreshTokenIn, SessionOut, UserOut
from app.auth import service
from app.auth.deps import DbSession, OptionalUser
from app.auth.providers import (
    InvalidIdTokenError,
    Provider,
    ProviderNotConfiguredError,
    verify_id_token,
)
from app.config import get_settings
from app.models import User
from app.ratelimit import RateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])
guest_limiter = RateLimiter(window_seconds=3600)


def _session(user: User, tokens: service.TokenPair) -> SessionOut:
    return SessionOut(
        user=UserOut.model_validate(user),
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post("/guest", status_code=status.HTTP_201_CREATED)
def create_guest(request: Request, db: DbSession) -> SessionOut:
    address = request.client.host if request.client else "unknown"
    if not guest_limiter.allow(address, get_settings().guest_accounts_per_hour):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_guest_accounts")
    user = service.create_guest(db)
    return _session(user, service.issue_tokens(db, user))


@router.post("/refresh")
def refresh(body: RefreshTokenIn, db: DbSession) -> SessionOut:
    try:
        user, tokens = service.rotate_refresh_token(db, body.refresh_token)
    except service.InvalidRefreshTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_refresh_token") from exc
    return _session(user, tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshTokenIn, db: DbSession) -> None:
    service.logout(db, body.refresh_token)


@router.post("/{provider}")
def login(
    provider: Provider, body: IdTokenIn, db: DbSession, current_user: OptionalUser
) -> SessionOut:
    try:
        profile = verify_id_token(provider, body.id_token)
    except ProviderNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "provider_not_configured") from exc
    except InvalidIdTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_id_token") from exc

    user = service.login_with_provider(db, profile, current_user)
    return _session(user, service.issue_tokens(db, user))
