"""Dashboard KPI computation.

Every figure here is derived from recorded data: the activity event log and
the operational tables. Nothing is hardcoded.

Each metric returns ``None`` when the recorded history is not sufficient to
state it. A KPI rendered as zero is a claim that work did not happen, which
is worse than showing nothing. The frontend renders "no data yet" for null.

Formulae
--------
Order accuracy
    Units shipped divided by units ordered, across orders that reached SHIPPED.
    Under 100% means the warehouse shipped short.

Picks per hour
    Sales orders that entered PICKING within the window, divided by the
    working hours elapsed in that window.

Dock to stock
    Mean hours between a goods receipt and its Quality approval, for orders
    that completed the QC gate within the window.

Inventory turnover
    Cost of goods sold divided by average inventory value. COGS is approximated
    from shipped sales lines valued at standard cost.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity import ActivityEvent
from app.models.demand import DemandAction, DemandLine
from app.models.item import Item
from app.models.purchasing import (
    PurchaseOrder,
    PurchaseOrderStatus,
)
from app.models.routing import ShipmentRoute
from app.models.sales import SalesOrder, SalesOrderLine, SalesOrderStatus
from app.schemas.dashboard import Kpi


def _window_start(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


def order_accuracy(db: Session, company_code: str, days: int = 30) -> Kpi:
    """Percentage of ordered units that were actually shipped."""
    since = _window_start(days)

    rows = db.execute(
        select(
            func.coalesce(func.sum(SalesOrderLine.quantity), 0),
            func.coalesce(func.sum(SalesOrderLine.qty_shipped), 0),
        )
        .join(SalesOrder, SalesOrder.id == SalesOrderLine.order_id)
        .where(SalesOrder.company_code == company_code)
        .where(SalesOrder.status.in_([SalesOrderStatus.SHIPPED, SalesOrderStatus.INVOICED]))
        .where(SalesOrder.order_date >= since.date())
    ).one()

    ordered, shipped = Decimal(str(rows[0])), Decimal(str(rows[1]))
    if ordered == 0:
        return Kpi(key="order_accuracy", value=None, unit="%")

    return Kpi(key="order_accuracy", value=round(float(shipped / ordered * 100), 1), unit="%")


def picks_per_hour(db: Session, company_code: str, days: int = 30) -> Kpi:
    """Average orders started for picking per hour of activity.

    The rate is measured across the span in which picking actually happened,
    not across the whole calendar window. Six orders spread over a month
    divided by 240 working hours reports "0.0 picks per hour", which reads as
    "nobody picked anything" when the warehouse was simply idle at weekends.

    The span is floored at one hour so a lone event still produces a rate.
    """
    since = _window_start(days)

    events = db.execute(
        select(ActivityEvent.occurred_at)
        .where(ActivityEvent.company_code == company_code)
        .where(ActivityEvent.entity == "sales_order")
        .where(ActivityEvent.action == "status_changed")
        .where(ActivityEvent.occurred_at >= since)
        .where(ActivityEvent.payload["to"].as_string() == SalesOrderStatus.PICKING.value)
        .order_by(ActivityEvent.occurred_at)
    ).scalars().all()

    if not events:
        return Kpi(key="picks_per_hour", value=None, unit="orders/h")

    timestamps = [_as_aware(value) for value in events]
    span_hours = max((timestamps[-1] - timestamps[0]).total_seconds() / 3600, 1.0)

    return Kpi(key="picks_per_hour", value=round(len(events) / span_hours, 1), unit="orders/h")


def dock_to_stock_hours(db: Session, company_code: str, days: int = 90) -> Kpi:
    """Mean hours between goods receipt and Quality approval."""
    since = _window_start(days)

    receipts = {
        event.entity_id: event.occurred_at
        for event in db.scalars(
            select(ActivityEvent).where(
                ActivityEvent.company_code == company_code,
                ActivityEvent.entity == "purchase_order",
                ActivityEvent.action == "received",
                ActivityEvent.occurred_at >= since,
            )
        ).all()
        if event.entity_id is not None
    }

    if not receipts:
        return Kpi(key="dock_to_stock", value=None, unit="h")

    durations: list[float] = []
    for event in db.scalars(
        select(ActivityEvent).where(
            ActivityEvent.company_code == company_code,
            ActivityEvent.entity == "purchase_order",
            ActivityEvent.action == "qc_approved",
            ActivityEvent.occurred_at >= since,
        )
    ).all():
        received_at = receipts.get(event.entity_id) if event.entity_id else None
        if received_at is None:
            continue
        delta = _as_aware(event.occurred_at) - _as_aware(received_at)
        durations.append(delta.total_seconds() / 3600)

    if not durations:
        return Kpi(key="dock_to_stock", value=None, unit="h")

    return Kpi(key="dock_to_stock", value=round(sum(durations) / len(durations), 1), unit="h")


def inventory_turnover(db: Session, company_code: str, days: int = 90) -> Kpi:
    """Cost of goods sold divided by average inventory value.

    A snapshot-based measure. With a single inventory reading the current
    value is used for both the opening and closing balance, so the number is
    indicative rather than exact until historical snapshots exist.
    """
    since = _window_start(days)

    cogs = db.scalar(
        select(func.coalesce(func.sum(SalesOrderLine.quantity * SalesOrderLine.unit_price), 0))
        .join(SalesOrder, SalesOrder.id == SalesOrderLine.order_id)
        .where(SalesOrder.company_code == company_code)
        .where(SalesOrder.status.in_([SalesOrderStatus.SHIPPED, SalesOrderStatus.INVOICED]))
        .where(SalesOrder.order_date >= since.date())
    )
    inventory = db.scalar(
        select(func.coalesce(func.sum(Item.stock * Item.unit_cost), 0)).where(
            Item.company_code == company_code
        )
    )

    if not inventory or Decimal(str(inventory)) == 0:
        return Kpi(key="inventory_turnover", value=None, unit="x")

    return Kpi(
        key="inventory_turnover",
        value=round(float(Decimal(str(cogs)) / Decimal(str(inventory))), 1),
        unit="x",
    )


def _as_aware(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime.

    SQLite has no native datetime type and drops the offset on read, so a
    value written as aware comes back naive. Arithmetic between the two
    raises, so every timestamp is normalised before subtraction.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def compute_all(db: Session, company_code: str) -> list[Kpi]:
    """Compute every dashboard KPI for a company."""
    return [
        order_accuracy(db, company_code),
        picks_per_hour(db, company_code),
        dock_to_stock_hours(db, company_code),
        inventory_turnover(db, company_code),
    ]


def operational_counts(db: Session, company_code: str) -> dict[str, int | Decimal]:
    """Headline counts shown alongside the KPIs."""
    open_sales = db.scalar(
        select(func.count())
        .select_from(SalesOrder)
        .where(SalesOrder.company_code == company_code)
        .where(SalesOrder.status.in_([SalesOrderStatus.OPEN, SalesOrderStatus.PICKING]))
    )

    open_purchases = db.scalar(
        select(func.count())
        .select_from(PurchaseOrder)
        .where(PurchaseOrder.company_code == company_code)
        .where(
            PurchaseOrder.status.in_(
                [
                    PurchaseOrderStatus.OPEN,
                    PurchaseOrderStatus.RECEIVED,
                    PurchaseOrderStatus.QC_PENDING,
                ]
            )
        )
    )

    awaiting_quality = db.scalar(
        select(func.count())
        .select_from(PurchaseOrder)
        .where(PurchaseOrder.company_code == company_code)
        .where(PurchaseOrder.status == PurchaseOrderStatus.QC_PENDING)
    )

    pending_demand = db.scalar(
        select(func.count())
        .select_from(DemandLine)
        .where(DemandLine.company_code == company_code)
        .where(DemandLine.action == DemandAction.PENDING)
    )

    below_minimum = db.scalar(
        select(func.count())
        .select_from(Item)
        .where(Item.company_code == company_code)
        .where(Item.stock < Item.min_stock)
    )

    inventory_value = db.scalar(
        select(func.coalesce(func.sum(Item.stock * Item.unit_cost), 0)).where(
            Item.company_code == company_code
        )
    )

    today = datetime.now(UTC).date()
    routes_today = db.scalar(
        select(func.count())
        .select_from(ShipmentRoute)
        .where(ShipmentRoute.company_code == company_code)
        .where(ShipmentRoute.date == today)
    )

    return {
        "open_sales_orders": open_sales or 0,
        "open_purchase_orders": open_purchases or 0,
        "orders_awaiting_quality": awaiting_quality or 0,
        "pending_demand_lines": pending_demand or 0,
        "items_below_minimum": below_minimum or 0,
        "inventory_value": Decimal(str(inventory_value or 0)),
        "routes_today": routes_today or 0,
    }


def alerts(db: Session, company_code: str) -> list[dict[str, str]]:
    """Operational warnings for the dashboard alert panel."""
    alerts: list[dict[str, str]] = []

    low_stock = db.execute(
        select(Item.code, Item.description, Item.stock, Item.min_stock)
        .where(Item.company_code == company_code)
        .where(Item.stock < Item.min_stock)
    ).all()

    for code, description, stock, min_stock in low_stock:
        alerts.append(
            {
                "severity": "critical",
                "code": code,
                "message": f"{code} · {description}: stock {stock} below minimum {min_stock}",
            }
        )

    awaiting_qc = db.scalar(
        select(func.count())
        .select_from(PurchaseOrder)
        .where(PurchaseOrder.company_code == company_code)
        .where(PurchaseOrder.status == PurchaseOrderStatus.QC_PENDING)
    )
    if awaiting_qc:
        alerts.append(
            {
                "severity": "warning",
                "code": "QC",
                "message": f"{awaiting_qc} purchase order(s) waiting for a Quality decision",
            }
        )

    overdue = db.execute(
        select(func.count())
        .select_from(PurchaseOrder)
        .where(PurchaseOrder.company_code == company_code)
        .where(PurchaseOrder.status == PurchaseOrderStatus.OPEN)
        .where(PurchaseOrder.expected_date < datetime.now(UTC).date())
    ).scalar()

    if overdue:
        alerts.append(
            {
                "severity": "warning",
                "code": "LATE",
                "message": f"{overdue} purchase order(s) past their expected delivery date",
            }
        )

    return alerts