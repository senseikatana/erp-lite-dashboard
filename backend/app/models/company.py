"""Company registry (multi-tenancy root)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.partner import Customer, Vendor
    from app.models.user import User


class Company(Base, TimestampMixin):
    """A registered company.

    The original prototype gave each company its own SQLite file. This project
    uses a single database with a ``company_code`` discriminator instead, so a
    user can be granted access to more than one company without duplicating the
    user table into every database file.
    """

    __tablename__ = "companies"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="es_ES", nullable=False)
    logo_path: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    default_language: Mapped[str] = mapped_column(String(5), default="es", nullable=False)

    # When true, received goods stay in QC_PENDING until Quality approves them.
    quality_check_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Which modules are visible for this company.
    modules_enabled: Mapped[list[str]] = mapped_column(
        JSON,
        default=lambda: ["dashboard", "sales", "purchases", "warehouse", "demand", "routes"],
        nullable=False,
    )

    users: Mapped[list[User]] = relationship(
        secondary="user_company_access",
        viewonly=True,
    )
    customers: Mapped[list[Customer]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    vendors: Mapped[list[Vendor]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )