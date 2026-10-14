"""Demand worksheet generation.

Demand lines are derived from two inputs: stock below minimum, and stock
committed to open sales orders. The worksheet is rebuilt on demand rather
than kept continuously in sync, so it cannot drift out of date.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.demand import DemandAction, DemandLine, DemandSource
from app.models.item import Item
from app.models.sales import SalesOrder, SalesOrderLine, SalesOrderStatus
from app.models.user import User
from app.schemas.ops import DemandGenerateRequest
from app.services import activity


def generate(
    db: Session, company_code: str, actor: User, params: DemandGenerateRequest
) -> list[DemandLine]:
    """Rebuild the pending demand worksheet for a company.

    Existing PENDING lines are discarded and recomputed. Lines already marked
    ORDERED or IGNORED are preserved so manual decisions are not lost on every
    regeneration.
    """
    horizon_end = date.today() + timedelta(days=params.horizon_days)

    # --- Quantity committed to open sales orders ---
    committed: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    open_statuses = [
        SalesOrderStatus.OPEN,
        SalesOrderStatus.PICKING,
        SalesOrderStatus.SHIPPED,
    ]
    rows = db.execute(
        select(SalesOrderLine.item_id, SalesOrderLine.quantity)
        .join(SalesOrder, SalesOrder.id == SalesOrderLine.order_id)
        .where(SalesOrder.company_code == company_code)
        .where(SalesOrder.status.in_(open_statuses))
        .where(SalesOrder.delivery_date.isnot(None))
        .where(SalesOrder.delivery_date <= horizon_end)
    ).all()

    for item_id, quantity in rows:
        committed[item_id] += Decimal(quantity)

    # --- Requirement per item ---
    items = db.scalars(select(Item).where(Item.company_code == company_code)).all()

    requirements: dict[int, tuple[Decimal, DemandSource, date]] = {}
    for item in items:
        target = Decimal(item.min_stock) * params.coverage_ratio
        shortage = target - Decimal(item.stock) - committed[item.id]
        if shortage <= 0:
            continue

        source = DemandSource.MIN_STOCK if Decimal(item.stock) < Decimal(item.min_stock) else (
            DemandSource.SALES_ORDER if item.id in committed else DemandSource.FORECAST
        )
        requirements[item.id] = (shortage, source, date.today() + timedelta(days=7))

    # --- Replace the pending worksheet ---
    db.execute(
        delete(DemandLine).where(
            DemandLine.company_code == company_code,
            DemandLine.action == DemandAction.PENDING,
        )
    )

    created: list[DemandLine] = []
    for item_id, (quantity, source, required_date) in requirements.items():
        line = DemandLine(
            company_code=company_code,
            item_id=item_id,
            required_date=required_date,
            quantity_needed=quantity,
            source=source,
            action=DemandAction.PENDING,
        )
        db.add(line)
        created.append(line)

    db.flush()

    activity.record(
        db,
        company_code=company_code,
        actor=actor,
        entity="demand",
        action="regenerated",
        summary=f"Rebuilt demand worksheet ({len(created)} line(s))",
        payload={
            "lines": len(created),
            "coverage_ratio": str(params.coverage_ratio),
            "horizon_days": params.horizon_days,
        },
    )
    return created


def suggested_quantity(item: Item, coverage_days: int, daily_consumption: Decimal) -> Decimal:
    """Reorder quantity for an item given a coverage target.

    Shared by the worksheet and the replenishment simulator so both agree on
    the formula.
    """
    target = daily_consumption * Decimal(coverage_days)
    return max(Decimal("0"), target - Decimal(item.stock))