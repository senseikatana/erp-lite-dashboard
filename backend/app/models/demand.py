"""Demand worksheet lines."""

from __future__ import annotations

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CompanyScopedMixin, TimestampMixin
from app.models.partner import Quantity

if TYPE_CHECKING:
    from app.models.item import Item


class DemandSource(enum.StrEnum):
    """Why a demand line exists."""

    SALES_ORDER = "SALES_ORDER"
    MIN_STOCK = "MIN_STOCK"
    FORECAST = "FORECAST"


class DemandAction(enum.StrEnum):
    PENDING = "PENDING"
    ORDERED = "ORDERED"
    IGNORED = "IGNORED"


class DemandLine(Base, CompanyScopedMixin, TimestampMixin):
    """A consolidated purchase requirement.

    Demand lines are derived data. They are rebuilt from sales orders and
    minimum stock levels rather than edited by hand, which is why the table
    carries no free-text notes.
    """

    __tablename__ = "demand_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)
    required_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_needed: Mapped[Decimal] = mapped_column(
        Quantity, default=Decimal("0"), nullable=False
    )
    source: Mapped[DemandSource] = mapped_column(
        Enum(DemandSource, native_enum=False, length=20), nullable=False
    )
    action: Mapped[DemandAction] = mapped_column(
        Enum(DemandAction, native_enum=False, length=20),
        default=DemandAction.PENDING,
        nullable=False,
        index=True,
    )

    item: Mapped[Item] = relationship(lazy="selectin")