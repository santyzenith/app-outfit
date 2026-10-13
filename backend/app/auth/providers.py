from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import jwt

from app.config import get_settings

Provider = Literal["google", "apple"]


@dataclass(frozen=True)
class ProviderConfig:
    issuers: tuple[str, ...]
    jwks_url: str


PROVIDERS: dict[str, ProviderConfig] = {
    "google": ProviderConfig(
        issuers=("https://accounts.google.com", "accounts.google.com"),
        jwks_url="https://www.googleapis.com/oauth2/v3/certs",
    ),
    "apple": ProviderConfig(
        issuers=("https://appleid.apple.com",),
        jwks_url="https://appleid.apple.com/auth/keys",
    ),
}


@dataclass(frozen=True)
class SocialProfile:
    provider: str
    subject: str
    email: str | None
    name: str | None


class InvalidIdTokenError(Exception):
    pass


class ProviderNotConfiguredError(Exception):
    pass


@lru_cache
def _jwks_client(provider: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(PROVIDERS[provider].jwks_url, cache_keys=True)


def verify_id_token(provider: Provider, id_token: str) -> SocialProfile:
    audiences = get_settings().client_ids(provider)
    if not audiences:
        raise ProviderNotConfiguredError(provider)

    try:
        signing_key = _jwks_client(provider).get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audiences,
            issuer=list(PROVIDERS[provider].issuers),
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidIdTokenError(str(exc)) from exc

    return SocialProfile(
        provider=provider,
        subject=claims["sub"],
        email=claims.get("email"),
        name=claims.get("name"),
    )
