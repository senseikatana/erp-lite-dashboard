"""Sales orders and their lines."""

from __future__ import annotations

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CompanyScopedMixin, TimestampMixin
from app.models.partner import Money, Quantity

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.partner import Customer


class SalesOrderStatus(enum.StrEnum):
    """Lifecycle of a sales order.

    OPEN -> PICKING -> SHIPPED -> INVOICED
    """

    OPEN = "OPEN"
    PICKING = "PICKING"
    SHIPPED = "SHIPPED"
    INVOICED = "INVOICED"
    CANCELLED = "CANCELLED"


class SalesOrder(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)

    order_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    delivery_date: Mapped[date | None] = mapped_column(Date)

    status: Mapped[SalesOrderStatus] = mapped_column(
        Enum(SalesOrderStatus, native_enum=False, length=20),
        default=SalesOrderStatus.OPEN,
        nullable=False,
        index=True,
    )

    total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    customer: Mapped[Customer] = relationship(back_populates="orders")
    lines: Mapped[list[SalesOrderLine]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    def recalculate_total(self) -> Decimal:
        """Recompute the header total from its lines and persist the result."""
        self.total = sum(
            (Decimal(line.quantity) * Decimal(line.unit_price) for line in self.lines),
            Decimal("0"),
        )
        return self.total


class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)

    quantity: Mapped[Decimal] = mapped_column(Quantity, default=Decimal("1"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)

    # Progress counters. The timestamps that turn these into measurable KPIs
    # live in the activity event log, not here.
    qty_picked: Mapped[Decimal] = mapped_column(Quantity, default=Decimal("0"), nullable=False)
    qty_shipped: Mapped[Decimal] = mapped_column(Quantity, default=Decimal("0"), nullable=False)

    order: Mapped[SalesOrder] = relationship(back_populates="lines")
    item: Mapped[Item] = relationship(lazy="selectin")

    @property
    def line_total(self) -> Decimal:
        return Decimal(self.quantity) * Decimal(self.unit_price)