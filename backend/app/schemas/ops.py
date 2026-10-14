"""Demand worksheet, routing and activity schemas."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from app.models.demand import DemandAction, DemandSource
from app.models.routing import RouteStatus
from app.schemas.common import ORMModel, QuantityOut


class DemandLineRead(ORMModel):
    id: int
    item_id: int
    item_code: str | None = None
    item_description: str | None = None
    required_date: datetime.date
    quantity_needed: QuantityOut
    source: DemandSource
    action: DemandAction


class DemandLineUpdate(ORMModel):
    action: DemandAction


class DemandGenerateRequest(ORMModel):
    """Parameters for rebuilding the demand worksheet.

    ``coverage_ratio`` multiplies the minimum stock level. The prototype used
    a hardcoded factor of 2, which made the worksheet impossible to tune.
    """

    coverage_ratio: Decimal = Field(default=Decimal("1.5"), gt=0)
    horizon_days: int = Field(default=30, gt=0, le=365)


class RouteRead(ORMModel):
    id: int
    code: str
    carrier: str
    # Annotated as datetime.date because the field is itself named `date`,
    # which would otherwise shadow the type during annotation resolution.
    date: datetime.date
    status: RouteStatus
    stops: int


class RouteCreate(ORMModel):
    code: str = Field(min_length=1, max_length=20)
    carrier: str = Field(min_length=1, max_length=60)
    date: datetime.date
    status: RouteStatus = RouteStatus.PLANNED
    stops: int = Field(default=0, ge=0)


class RouteUpdate(ORMModel):
    carrier: str | None = None
    date: datetime.date | None = None
    status: RouteStatus | None = None
    stops: int | None = Field(default=None, ge=0)


class ActivityEventRead(ORMModel):
    id: int
    occurred_at: datetime.datetime
    actor_username: str
    entity: str
    entity_id: int | None
    action: str
    summary: str | None = None
    payload: dict[str, Any] | None = None