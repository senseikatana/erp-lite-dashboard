"""Declarative base and shared model mixins."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

# Re-exported so model modules import Base, mixins and helpers from one place.
from app.core.database import Base

__all__ = ["Base", "CompanyScopedMixin", "TimestampMixin", "utcnow"]


def utcnow() -> datetime:
    """Return an aware UTC timestamp.

    The original schema used ``datetime.utcnow`` for column defaults, which
    returns a naive datetime and is deprecated since Python 3.12. Every
    timestamp in the schema is timezone-aware instead.
    """
    return datetime.now(UTC)


class TimestampMixin:
    """Adds creation and modification timestamps to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class CompanyScopedMixin:
    """Binds a row to a company for multi-tenant isolation.

    Every query the application issues filters on ``company_code``. That
    filtering is not optional: it is the tenant boundary. See
    ``app.api.deps.current_company``.
    """

    company_code: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("companies.code", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )