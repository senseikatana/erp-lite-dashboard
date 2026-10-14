"""Shared pytest fixtures.

Every test runs against a temporary SQLite database so the suite never touches
a developer's working data.
"""

from __future__ import annotations

import os

import pytest

# Point the settings layer at an in-memory database before any app module is
# imported, otherwise `get_settings()` would cache the real URL. In-memory keeps
# the suite hermetic: no file, no stale state left by an interrupted run, and
# no way to touch a developer's working data.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-not-used-in-production-0123456789"
os.environ["ENVIRONMENT"] = "test"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import Base, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Company, Role, User, UserCompanyAccess  # noqa: E402

TEST_PASSWORD = "testpass123"


@pytest.fixture(autouse=True)
def clean_database():
    """Reset the schema around each test.

    The engine is deliberately not disposed here: against an in-memory
    database that closes the single pinned connection and destroys the
    database itself. Dropping and recreating the schema is enough.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Session:
    with Session(engine) as session:
        yield session


@pytest.fixture
def seeded(db: Session) -> dict:
    """Minimal company and one user per role."""
    company = Company(code="TEST_CO", name="Test Company")
    db.add(company)
    db.commit()

    users = {}
    for role in Role:
        user = User(username=role.value, full_name=role.value.title(), role=role)
        user.set_password(TEST_PASSWORD)
        db.add(user)
        db.flush()
        db.add(UserCompanyAccess(user_id=user.id, company_code="TEST_CO"))
        users[role] = user

    db.commit()
    return {"company": company, "users": users}


def _token(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def client(db: Session) -> TestClient:
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client: TestClient, seeded: dict):
    """Factory producing an Authorization header for a given role."""

    def _build(role: Role) -> dict[str, str]:
        return {"Authorization": f"Bearer {_token(client, role.value)}"}

    return _build