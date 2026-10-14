"""Sales order schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, model_validator

from app.models.sales import SalesOrderStatus
from app.schemas.common import MoneyOut, ORMModel, QuantityOut


class SalesOrderLineRead(ORMModel):
    id: int
    item_id: int
    item_code: str | None = None
    item_description: str | None = None
    quantity: QuantityOut
    unit_price: MoneyOut
    line_total: MoneyOut = Decimal("0")
    qty_picked: QuantityOut
    qty_shipped: QuantityOut


class SalesOrderRead(ORMModel):
    id: int
    number: str
    customer_id: int
    customer_name: str | None = None
    order_date: date
    delivery_date: date | None = None
    status: SalesOrderStatus
    total: MoneyOut
    notes: str | None = None
    created_at: datetime | None = None
    lines: list[SalesOrderLineRead] = []


class SalesOrderLineCreate(ORMModel):
    item_id: int
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)


class SalesOrderCreate(ORMModel):
    customer_id: int
    delivery_date: date | None = None
    notes: str | None = None
    lines: list[SalesOrderLineCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_lines(self) -> SalesOrderCreate:
        if not self.lines:
            raise ValueError("A sales order must contain at least one line")
        return self


class SalesOrderUpdate(ORMModel):
    delivery_date: date | None = None
    notes: str | None = None


class SalesOrderLineUpdate(ORMModel):
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)


class StatusChange(ORMModel):
    """Request body for a workflow transition.

    A bare status string is not accepted anywhere in the API: transitions are
    validated server-side against the allowed graph, because a client sending
    ``INVOICED`` to a fresh order is a bug we want to reject loudly.
    """

    status: SalesOrderStatus
    reason: str | None = Field(default=None, max_length=200)