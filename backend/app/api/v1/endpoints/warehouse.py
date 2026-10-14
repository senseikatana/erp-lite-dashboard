"""Warehouse and item endpoints."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentCompany, DbSession, PageParams, paginate, require_roles
from app.models.item import Item
from app.models.user import Role, User
from app.schemas.common import Page, PageMeta
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate, StockAdjust
from app.services import activity

router = APIRouter(prefix="/warehouse", tags=["warehouse"])

# Managing the item master and stock is a warehouse responsibility. Declared
# once here so create, update and adjust cannot drift apart.
WarehouseOperator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.LOGISTICS))]


@router.get("/items", response_model=Page[ItemRead])
def list_items(
    db: DbSession,
    company: CurrentCompany,
    page: PageParams,
    search: str | None = Query(default=None, description="Match against code or description"),
    below_minimum: bool = Query(default=False),
    location: str | None = None,
) -> Page[ItemRead]:
    """List inventory items with optional filters."""
    query = select(Item).where(Item.company_code == company.code)

    if search:
        pattern = f"%{search}%"
        query = query.where(Item.code.ilike(pattern) | Item.description.ilike(pattern))

    if below_minimum:
        query = query.where(Item.stock < Item.min_stock)

    if location:
        query = query.where(Item.location == location)

    query = query.order_by(Item.code)

    rows, total = paginate(db, query, page)
    return Page[ItemRead](
        items=[ItemRead.model_validate(row) for row in rows],
        meta=PageMeta(total=total, limit=page.limit, offset=page.offset),
    )


@router.get("/locations")
def list_locations(db: DbSession, company: CurrentCompany) -> list[dict]:
    """Stock aggregated by warehouse location."""
    from sqlalchemy import func

    rows = db.execute(
        select(Item.location, func.sum(Item.stock), func.count(Item.id))
        .where(Item.company_code == company.code)
        .group_by(Item.location)
        .order_by(Item.location)
    ).all()

    return [
        {"location": location, "total_stock": float(total or 0), "item_count": count}
        for location, total, count in rows
    ]


@router.get("/items/{item_id}", response_model=ItemRead)
def read_item(item_id: int, db: DbSession, company: CurrentCompany) -> Item:
    item = db.scalar(
        select(Item).where(Item.id == item_id, Item.company_code == company.code)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/items", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate, db: DbSession, user: WarehouseOperator, company: CurrentCompany
) -> Item:
    """Create an item. Logistics and administrators only."""
    existing = db.scalar(
        select(Item).where(Item.company_code == company.code, Item.code == payload.code)
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Item code '{payload.code}' already exists")

    item = Item(company_code=company.code, **payload.model_dump())
    db.add(item)
    db.flush()

    activity.record(
        db,
        company_code=company.code,
        actor=user,
        entity="item",
        action="created",
        entity_id=item.id,
        summary=f"Created item {item.code}",
        payload={"code": item.code, "description": item.description},
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch("/items/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int,
    payload: ItemUpdate,
    db: DbSession,
    user: WarehouseOperator,
    company: CurrentCompany,
) -> Item:
    """Update item master data. Logistics and administrators only."""
    item = db.scalar(
        select(Item).where(Item.id == item_id, Item.company_code == company.code)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    # Stock is deliberately not editable here. It moves through receipts,
    # Quality approvals and explicit adjustments so every change has a reason
    # and an author in the activity log.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    activity.record(
        db,
        company_code=company.code,
        actor=user,
        entity="item",
        action="updated",
        entity_id=item.id,
        summary=f"Updated item {item.code}",
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/items/{item_id}/adjust", response_model=ItemRead)
def adjust_stock(
    item_id: int,
    payload: StockAdjust,
    db: DbSession,
    user: WarehouseOperator,
    company: CurrentCompany,
) -> Item:
    """Post a manual stock correction.

    Every adjustment is logged with the reason, so a stock discrepancy can
    always be traced back to a person and a justification.
    """
    item = db.scalar(
        select(Item).where(Item.id == item_id, Item.company_code == company.code)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    previous = Decimal(item.stock)
    updated = previous + Decimal(payload.quantity)

    if updated < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Adjustment would drive stock negative ({updated})",
        )

    item.stock = updated

    activity.record(
        db,
        company_code=company.code,
        actor=user,
        entity="item",
        action="stock_adjusted",
        entity_id=item.id,
        summary=f"Adjusted {item.code} by {payload.quantity}",
        payload={
            "previous": str(previous),
            "new": str(updated),
            "delta": str(payload.quantity),
            "reason": payload.reason,
        },
    )
    db.commit()
    db.refresh(item)
    return item