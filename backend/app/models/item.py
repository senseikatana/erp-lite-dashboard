"""Inventory items."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CompanyScopedMixin, TimestampMixin
from app.models.partner import Money, Quantity

if TYPE_CHECKING:
    pass


class Item(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), default="EA", nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)

    stock: Mapped[Decimal] = mapped_column(Quantity, default=Decimal("0"), nullable=False)
    min_stock: Mapped[Decimal] = mapped_column(Quantity, default=Decimal("0"), nullable=False)

    location: Mapped[str] = mapped_column(String(20), default="A-01", nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(50))

    @property
    def is_below_minimum(self) -> bool:
        return Decimal(self.stock) < Decimal(self.min_stock)

    @property
    def stock_ratio(self) -> Decimal:
        """Stock expressed as a multiple of the minimum.

        Returns 0 when no minimum is set, so the dashboard never divides by
        zero.
        """
        min_stock = Decimal(self.min_stock)
        if min_stock == 0:
            return Decimal("0")
        return Decimal(self.stock) / min_stock