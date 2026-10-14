"""Demand worksheet and shipment route endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentCompany, DbSession, PageParams, paginate, require_roles
from app.models.activity import ActivityEvent
from app.models.demand import DemandAction, DemandLine
from app.models.routing import RouteStatus, ShipmentRoute
from app.models.user import Role, User
from app.schemas.common import Page, PageMeta
from app.schemas.ops import (
    ActivityEventRead,
    DemandGenerateRequest,
    DemandLineRead,
    DemandLineUpdate,
    RouteCreate,
    RouteRead,
    RouteUpdate,
)
from app.services import activity as activity_log
from app.services import demand_service

router = APIRouter(tags=["planning"])

# The demand worksheet is a purchasing tool; transport planning is not.
Planner = Annotated[User, Depends(require_roles(Role.ADMIN, Role.BUYER))]
Dispatcher = Annotated[User, Depends(require_roles(Role.ADMIN, Role.LOGISTICS))]


# --- Demand worksheet ---


@router.get("/demand", response_model=Page[DemandLineRead])
def list_demand(
    db: DbSession,
    company: CurrentCompany,
    page: PageParams,
    action_filter: DemandAction | None = Query(default=None, alias="action"),
) -> Page[DemandLineRead]:
    """List demand worksheet lines, pending ones by default."""
    query = select(DemandLine).where(DemandLine.company_code == company.code)

    if action_filter:
        query = query.where(DemandLine.action == action_filter)

    query = query.order_by(DemandLine.required_date.asc(), DemandLine.id.asc())

    rows, total = paginate(db, query, page)
    return Page[DemandLineRead](
        items=[DemandLineRead.model_validate(row) for row in rows],
        meta=PageMeta(total=total, limit=page.limit, offset=page.offset),
    )


@router.post("/demand/generate", response_model=list[DemandLineRead])
def generate_demand(
    payload: DemandGenerateRequest,
    db: DbSession,
    user: Planner,
    company: CurrentCompany,
) -> list[DemandLine]:
    """Rebuild the demand worksheet from stock levels and open sales orders."""
    lines = demand_service.generate(db, company.code, user, payload)
    db.commit()
    return [DemandLineRead.model_validate(line) for line in lines]


@router.patch("/demand/{line_id}", response_model=DemandLineRead)
def update_demand_line(
    line_id: int,
    payload: DemandLineUpdate,
    db: DbSession,
    user: Planner,
    company: CurrentCompany,
) -> DemandLine:
    """Mark a demand line as ordered or ignored."""
    line = db.scalar(
        select(DemandLine).where(DemandLine.id == line_id, DemandLine.company_code == company.code)
    )
    if line is None:
        raise HTTPException(status_code=404, detail="Demand line not found")

    previous = line.action
    line.action = payload.action

    activity_log.record(
        db,
        company_code=company.code,
        actor=user,
        entity="demand",
        action="updated",
        entity_id=line.id,
        summary=f"{previous.value} -> {payload.action.value}",
        payload={"from": previous.value, "to": payload.action.value},
    )
    db.commit()
    db.refresh(line)
    return line


# --- Shipment routes ---


@router.get("/routes", response_model=Page[RouteRead])
def list_routes(
    db: DbSession,
    company: CurrentCompany,
    page: PageParams,
    status_filter: RouteStatus | None = Query(default=None, alias="status"),
) -> Page[RouteRead]:
    """List shipment routes."""
    query = select(ShipmentRoute).where(ShipmentRoute.company_code == company.code)

    if status_filter:
        query = query.where(ShipmentRoute.status == status_filter)

    query = query.order_by(ShipmentRoute.date.asc(), ShipmentRoute.code.asc())

    rows, total = paginate(db, query, page)
    return Page[RouteRead](
        items=[RouteRead.model_validate(row) for row in rows],
        meta=PageMeta(total=total, limit=page.limit, offset=page.offset),
    )


@router.post("/routes", response_model=RouteRead, status_code=status.HTTP_201_CREATED)
def create_route(
    payload: RouteCreate, db: DbSession, user: Dispatcher, company: CurrentCompany
) -> ShipmentRoute:
    """Plan a shipment route. Logistics and administrators only."""
    existing = db.scalar(
        select(ShipmentRoute).where(
            ShipmentRoute.company_code == company.code, ShipmentRoute.code == payload.code
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Route '{payload.code}' already exists")

    route = ShipmentRoute(company_code=company.code, **payload.model_dump())
    db.add(route)
    db.flush()

    activity_log.record(
        db,
        company_code=company.code,
        actor=user,
        entity="route",
        action="created",
        entity_id=route.id,
        summary=f"Planned route {route.code} with {route.stops} stop(s)",
    )
    db.commit()
    db.refresh(route)
    return route


@router.patch("/routes/{route_id}", response_model=RouteRead)
def update_route(
    route_id: int,
    payload: RouteUpdate,
    db: DbSession,
    user: Dispatcher,
    company: CurrentCompany,
) -> ShipmentRoute:
    """Update a route, typically to move it to IN_TRANSIT or DELIVERED."""
    route = db.scalar(
        select(ShipmentRoute).where(
            ShipmentRoute.id == route_id, ShipmentRoute.company_code == company.code
        )
    )
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")

    previous = route.status
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(route, field, value)

    activity_log.record(
        db,
        company_code=company.code,
        actor=user,
        entity="route",
        action="updated",
        entity_id=route.id,
        summary=f"Updated route {route.code}",
        payload={"status_from": previous.value, "status_to": route.status.value},
    )
    db.commit()
    db.refresh(route)
    return route


# --- Audit trail ---


@router.get("/activity", response_model=Page[ActivityEventRead])
def audit_trail(
    db: DbSession,
    company: CurrentCompany,
    page: PageParams,
    entity: str | None = None,
    action: str | None = None,
    actor: str | None = None,
) -> Page[ActivityEventRead]:
    """Query the activity log.

    This is the audit trail: who changed what, and when. Filters are additive
    and always scoped to the caller's company.
    """
    query = select(ActivityEvent).where(ActivityEvent.company_code == company.code)

    if entity:
        query = query.where(ActivityEvent.entity == entity)
    if action:
        query = query.where(ActivityEvent.action == action)
    if actor:
        query = query.where(ActivityEvent.actor_username == actor)

    query = query.order_by(ActivityEvent.occurred_at.desc(), ActivityEvent.id.desc())

    rows, total = paginate(db, query, page)
    return Page[ActivityEventRead](
        items=[ActivityEventRead.model_validate(row) for row in rows],
        meta=PageMeta(total=total, limit=page.limit, offset=page.offset),
    )