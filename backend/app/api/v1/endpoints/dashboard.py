"""Dashboard endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentCompany, DbSession
from app.models.activity import ActivityEvent
from app.models.item import Item
from app.models.routing import ShipmentRoute
from app.schemas.dashboard import DashboardSummary, RouteSummary, StockLevel
from app.schemas.ops import ActivityEventRead
from app.services import kpi_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: DbSession, company: CurrentCompany) -> DashboardSummary:
    """KPI block and headline counts for the dashboard.

    KPIs are computed from the activity log. Until enough events have been
    recorded a metric comes back null, which the client renders as "no data".
    """
    code = company.code
    return DashboardSummary(
        company_code=code,
        generated_at=datetime.now(UTC).isoformat(),
        kpis=kpi_service.compute_all(db, code),
        **kpi_service.operational_counts(db, code),
    )


@router.get("/alerts", response_model=list[dict[str, str]])
def alerts(db: DbSession, company: CurrentCompany) -> list[dict[str, str]]:
    """Operational warnings: low stock, Quality backlog, late suppliers."""
    return kpi_service.alerts(db, company.code)


@router.get("/stock-levels", response_model=list[StockLevel])
def stock_levels(db: DbSession, company: CurrentCompany) -> list[StockLevel]:
    """Items at or below their minimum stock level."""
    rows = db.execute(
        select(Item.id, Item.code, Item.description, Item.stock, Item.min_stock)
        .where(Item.company_code == company.code)
        .where(Item.stock <= Item.min_stock)
        .order_by(Item.code)
    ).all()

    return [
        StockLevel(
            item_id=item_id,
            code=code,
            description=description,
            stock=float(stock),
            min_stock=float(min_stock),
        )
        for item_id, code, description, stock, min_stock in rows
    ]


@router.get("/routes", response_model=list[RouteSummary])
def route_summary(db: DbSession, company: CurrentCompany) -> list[RouteSummary]:
    """Routes grouped by carrier for the dashboard chart."""
    rows = db.execute(
        select(ShipmentRoute.carrier, func.sum(ShipmentRoute.stops))
        .where(ShipmentRoute.company_code == company.code)
        .group_by(ShipmentRoute.carrier)
    ).all()

    return [
        RouteSummary(carrier=carrier, stops=int(stops or 0), status="")
        for carrier, stops in rows
    ]


@router.get("/activity", response_model=list[ActivityEventRead])
def recent_activity(
    db: DbSession, company: CurrentCompany, limit: int = 20
) -> list[ActivityEvent]:
    """Most recent recorded changes, newest first."""
    return list(
        db.scalars(
            select(ActivityEvent)
            .where(ActivityEvent.company_code == company.code)
            .order_by(ActivityEvent.occurred_at.desc(), ActivityEvent.id.desc())
            .limit(min(max(limit, 1), 200))
        ).all()
    )