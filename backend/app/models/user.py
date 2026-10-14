"""Users, roles and company grants."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import hash_password, verify_password
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company


# ``companies`` is resolved through the ``user_company_access`` secondary table.
# Reading ``user.companies`` yields Company rows directly rather than the
# join rows, which is what both the API schema and ``can_access`` expect.


class Role(enum.StrEnum):
    """Application roles.

    Roles are coarse by design. They map onto the departments that actually
    operate the warehouse: purchasing, logistics and quality, plus an
    administrator.

    Authorisation is enforced server-side. The frontend hides navigation
    entries for convenience, but the API is the security boundary.
    """

    ADMIN = "admin"
    BUYER = "buyer"
    LOGISTICS = "logistics"
    QUALITY = "quality"

    @property
    def label(self) -> str:
        return {
            Role.ADMIN: "Administrator",
            Role.BUYER: "Buyer",
            Role.LOGISTICS: "Logistics",
            Role.QUALITY: "Quality",
        }[self]


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(180), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, native_enum=False, length=20), default=Role.ADMIN, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    companies: Mapped[list[Company]] = relationship(
        secondary="user_company_access",
        lazy="selectin",
    )

    def set_password(self, raw_password: str) -> None:
        self.hashed_password = hash_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return verify_password(raw_password, self.hashed_password)

    def can_access(self, company_code: str) -> bool:
        """Whether this user may operate within a company.

        Administrators implicitly reach every registered company.
        """
        if self.role == Role.ADMIN:
            return True
        return any(company.code == company_code for company in self.companies)


class UserCompanyAccess(Base):
    """Grant linking a user to a company they may operate in."""

    __tablename__ = "user_company_access"
    __table_args__ = (UniqueConstraint("user_id", "company_code", name="uq_user_company"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("companies.code", ondelete="CASCADE"), nullable=False
    )

    user: Mapped[User] = relationship(viewonly=True)
    company: Mapped[Company] = relationship(viewonly=True)