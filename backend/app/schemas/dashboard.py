"""Dashboard and KPI schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.common import ORMModel, QuantityOut


class Kpi(ORMModel):
    """A single measured metric.

    ``value`` is null when there is not enough recorded activity to compute the
    figure. The frontend renders "no data yet" for null rather than showing a
    zero, because a zero KPI is a false statement about the business.
    """

    key: str
    value: float | None = None
    unit: str | None = None
    delta: float | None = Field(default=None, description="Change vs. the previous period")


class DashboardSummary(ORMModel):
    company_code: str
    generated_at: str

    kpis: list[Kpi] = []

    open_sales_orders: int = 0
    open_purchase_orders: int = 0
    orders_awaiting_quality: int = 0
    pending_demand_lines: int = 0

    items_below_minimum: int = 0
    inventory_value: QuantityOut = Decimal("0")
    routes_today: int = 0


class StockLevel(ORMModel):
    item_id: int
    code: str
    description: str
    stock: float
    min_stock: float


class RouteSummary(ORMModel):
    carrier: str
    stops: int
    status: str


class DailyThroughput(ORMModel):
    """Ordered and shipped quantities for a single day.

    Feeds the dashboard trend chart.
    """

    day: date
    picked: float
    shipped: float
    received: float