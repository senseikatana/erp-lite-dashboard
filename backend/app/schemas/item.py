"""Item schemas."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from app.schemas.common import ORMModel, QuantityOut


class ItemRead(ORMModel):
    id: int
    code: str
    description: str
    unit: str
    unit_cost: QuantityOut
    unit_price: QuantityOut
    stock: QuantityOut
    min_stock: QuantityOut
    location: str
    category: str | None = None
    is_below_minimum: bool = False


class ItemCreate(ORMModel):
    code: str = Field(min_length=1, max_length=30)
    description: str = Field(min_length=1, max_length=200)
    unit: str = "EA"
    unit_cost: Decimal = Field(default=Decimal("0"), ge=0)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    stock: Decimal = Field(default=Decimal("0"), ge=0)
    min_stock: Decimal = Field(default=Decimal("0"), ge=0)
    location: str = "A-01"
    category: str | None = None


class ItemUpdate(ORMModel):
    description: str | None = None
    unit: str | None = None
    unit_cost: Decimal | None = Field(default=None, ge=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    min_stock: Decimal | None = Field(default=None, ge=0)
    location: str | None = None
    category: str | None = None


class StockAdjust(ORMModel):
    """Manual stock correction.

    Negative quantities are allowed because a recount can go either way. The
    activity log records who made the correction and by how much.
    """

    quantity: Decimal
    reason: str = Field(min_length=1, max_length=200)