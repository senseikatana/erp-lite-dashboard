"""Purchase orders, receipts and the quality control gate."""

from __future__ import annotations

import enum
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CompanyScopedMixin, TimestampMixin
from app.models.partner import Money, Quantity

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.partner import Vendor


class PurchaseOrderStatus(enum.StrEnum):
    """Lifecycle of a purchase order.

    OPEN -> RECEIVED -> QC_PENDING -> QC_APPROVED -> CLOSED
    A rejected receipt returns the order to OPEN for the vendor to rework.
    """

    OPEN = "OPEN"
    RECEIVED = "RECEIVED"
    QC_PENDING = "QC_PENDING"
    QC_APPROVED = "QC_APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class QualityStatus(enum.StrEnum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class PurchaseOrder(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), nullable=False)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"), nullable=False)

    order_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    expected_date: Mapped[date | None] = mapped_column(Date)

    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(PurchaseOrderStatus, native_enum=False, length=20),
        default=PurchaseOrderStatus.OPEN,
        nullable=False,
        index=True,
    )

    total: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)

    vendor: Mapped[Vendor] = relationship(lazy="selectin")
    lines: Mapped[list[PurchaseOrderLine]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )

    def recalculate_total(self) -> Decimal:
        self.total = sum(
            (Decimal(line.quantity) * Decimal(line.unit_cost) for line in self.lines),
            Decimal("0"),
        )
        return self.total


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, index=True)

    quantity: Mapped[Decimal] = mapped_column(Quantity, default=Decimal("1"), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Money, default=Decimal("0"), nullable=False)
    qty_received: Mapped[Decimal] = mapped_column(Quantity, default=Decimal("0"), nullable=False)
    qc_status: Mapped[QualityStatus] = mapped_column(
        Enum(QualityStatus, native_enum=False, length=20),
        default=QualityStatus.PENDING,
        nullable=False,
    )

    # Whether this line's received quantity has already been posted to item
    # stock. Without it a re-opened or double-clipped Quality approval would
    # inflate inventory.
    stock_posted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    order: Mapped[PurchaseOrder] = relationship(back_populates="lines")
    item: Mapped[Item] = relationship(lazy="selectin")

    @property
    def line_total(self) -> Decimal:
        return Decimal(self.quantity) * Decimal(self.unit_cost)