"""Authentication and user schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import EmailStr, Field

from app.models.user import Role
from app.schemas.common import ORMModel


class LoginRequest(ORMModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=128)


class CompanyAccessRead(ORMModel):
    code: str
    name: str
    currency: str


class UserRead(ORMModel):
    id: int
    username: str
    email: EmailStr | None = None
    full_name: str
    role: Role
    is_active: bool
    companies: list[CompanyAccessRead] = []


class Token(ORMModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")
    user: UserRead
    active_company: str


class RefreshRequest(ORMModel):
    """Placeholder for refreshing a session.

    The current implementation issues a token valid for the whole working day
    and does not expose a refresh endpoint. This schema exists so adding one
    later does not require an API break.
    """

    username: str


class UserCreate(ORMModel):
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=8, max_length=128)
    email: EmailStr | None = None
    full_name: str = Field(min_length=1, max_length=120)
    role: Role = Role.ADMIN
    company_codes: list[str] = []


class UserUpdate(ORMModel):
    full_name: str | None = None
    email: EmailStr | None = None
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class ChangePasswordRequest(ORMModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class AuditEntry(ORMModel):
    """A recorded change, rendered for the audit view."""

    occurred_at: datetime
    actor_username: str
    entity: str
    entity_id: int | None
    action: str
    summary: str | None