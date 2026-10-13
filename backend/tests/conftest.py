import os
import tempfile
import time
from pathlib import Path

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://outfit:outfit@127.0.0.1:5433/outfit_test"
)
GOOGLE_CLIENT_ID = "google-client-id"
APPLE_CLIENT_ID = "apple-client-id"

# Settings are read at import time, so the test values go in before the app is imported.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET"] = "test-secret-with-enough-length-for-hs256"
os.environ["GOOGLE_CLIENT_IDS"] = GOOGLE_CLIENT_ID
os.environ["APPLE_CLIENT_IDS"] = APPLE_CLIENT_ID
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="outfit-test-storage-")

import jwt  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.api.auth import guest_limiter  # noqa: E402
from app.auth import providers  # noqa: E402
from app.db import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return config


@pytest.fixture(scope="session", autouse=True)
def migrated_database(alembic_config: Config) -> None:
    url = make_url(TEST_DATABASE_URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()

    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config, "head")


@pytest.fixture
def db() -> Session:
    # Each test runs inside a transaction that is rolled back at the end.
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def fresh_rate_limits() -> None:
    guest_limiter.reset()


@pytest.fixture
def client(db: Session) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


class _FakeJwksClient:
    def __init__(self, public_key) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str):
        return type("SigningKey", (), {"key": self._public_key})()


@pytest.fixture
def make_id_token(monkeypatch: pytest.MonkeyPatch):
    # Signs ID tokens with a local key that stands in for Google's and Apple's.
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    fake_client = _FakeJwksClient(private_key.public_key())
    monkeypatch.setattr(providers, "_jwks_client", lambda provider: fake_client)

    issuers = {"google": "https://accounts.google.com", "apple": "https://appleid.apple.com"}
    audiences = {"google": GOOGLE_CLIENT_ID, "apple": APPLE_CLIENT_ID}

    def build(provider: str = "google", subject: str = "user-1", **overrides) -> str:
        now = int(time.time())
        claims = {
            "iss": issuers[provider],
            "aud": audiences[provider],
            "sub": subject,
            "email": f"{subject}@example.com",
            "name": "Sofia Test",
            "iat": now,
            "exp": now + 600,
            **overrides,
        }
        return jwt.encode(claims, private_key, algorithm="RS256")

    return build


def auth_header(session_body: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {session_body['access_token']}"}
