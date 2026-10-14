"""Purchase order schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.models.purchasing import PurchaseOrderStatus, QualityStatus
from app.schemas.common import MoneyOut, ORMModel, QuantityOut


class PurchaseOrderLineRead(ORMModel):
    id: int
    item_id: int
    item_code: str | None = None
    item_description: str | None = None
    quantity: QuantityOut
    unit_cost: MoneyOut
    line_total: MoneyOut = Decimal("0")
    qty_received: QuantityOut
    qc_status: QualityStatus


class PurchaseOrderRead(ORMModel):
    id: int
    number: str
    vendor_id: int
    vendor_name: str | None = None
    order_date: date
    expected_date: date | None = None
    status: PurchaseOrderStatus
    total: MoneyOut
    created_at: datetime | None = None
    lines: list[PurchaseOrderLineRead] = []


class PurchaseOrderLineCreate(ORMModel):
    item_id: int
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)


class PurchaseOrderCreate(ORMModel):
    vendor_id: int
    expected_date: date | None = None
    lines: list[PurchaseOrderLineCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_lines(self) -> PurchaseOrderCreate:
        if not self.lines:
            raise ValueError("A purchase order must contain at least one line")
        return self


class PurchaseOrderUpdate(ORMModel):
    expected_date: date | None = None


class ReceiptRequest(ORMModel):
    """Goods receipt.

    Omitted line quantities default to the ordered quantity, which covers the
    common case of receiving a complete order in one pass.
    """

    lines: list[ReceiptLine] | None = None
    reference: str | None = Field(default=None, max_length=60)


class ReceiptLine(ORMModel):
    line_id: int
    quantity_received: Decimal = Field(ge=0)


class QualityDecisionRequest(ORMModel):
    """Quality inspection result.

    ``passed=False`` rejects the batch and returns the order to OPEN without
    touching inventory.
    """

    passed: bool
    note: str | None = Field(default=None, max_length=200)
    lines: list[QualityDecisionLine] | None = None


class QualityDecisionLine(ORMModel):
    line_id: int
    status: QualityStatus