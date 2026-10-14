"""Customer and vendor master data endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentCompany, DbSession, PageParams, paginate, require_roles
from app.models.partner import Customer, Vendor
from app.models.user import Role, User
from app.schemas.common import Page, PageMeta
from app.schemas.partner import (
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
    VendorCreate,
    VendorRead,
    VendorUpdate,
)
from app.services import activity

router = APIRouter(tags=["partners"])

# Supplier master data belongs to purchasing; customer master data is open to
# the warehouse as well, because logistics books deliveries for them.
Buyer = Annotated[User, Depends(require_roles(Role.ADMIN, Role.BUYER))]
CustomerEditor = Annotated[User, Depends(require_roles(Role.ADMIN, Role.BUYER, Role.LOGISTICS))]


# --- Customers ---


@router.get("/customers", response_model=Page[CustomerRead])
def list_customers(
    db: DbSession,
    company: CurrentCompany,
    page: PageParams,
    search: str | None = Query(default=None),
) -> Page[CustomerRead]:
    query = select(Customer).where(Customer.company_code == company.code)
    if search:
        pattern = f"%{search}%"
        query = query.where(Customer.name.ilike(pattern) | Customer.code.ilike(pattern))
    query = query.order_by(Customer.name)

    rows, total = paginate(db, query, page)
    return Page[CustomerRead](
        items=[CustomerRead.model_validate(row) for row in rows],
        meta=PageMeta(total=total, limit=page.limit, offset=page.offset),
    )


@router.get("/customers/{customer_id}", response_model=CustomerRead)
def read_customer(customer_id: int, db: DbSession, company: CurrentCompany) -> Customer:
    customer = db.scalar(
        select(Customer).where(Customer.id == customer_id, Customer.company_code == company.code)
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/customers", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate, db: DbSession, user: CustomerEditor, company: CurrentCompany
) -> Customer:
    existing = db.scalar(
        select(Customer).where(
            Customer.company_code == company.code, Customer.code == payload.code
        )
    )
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Customer code '{payload.code}' already exists"
        )

    customer = Customer(company_code=company.code, **payload.model_dump())
    db.add(customer)
    db.flush()

    activity.record(
        db,
        company_code=company.code,
        actor=user,
        entity="customer",
        action="created",
        entity_id=customer.id,
        summary=f"Created customer {customer.code}",
    )
    db.commit()
    db.refresh(customer)
    return customer


@router.patch("/customers/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: DbSession,
    user: Buyer,
    company: CurrentCompany,
) -> Customer:
    customer = db.scalar(
        select(Customer).where(Customer.id == customer_id, Customer.company_code == company.code)
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)
    return customer


# --- Vendors ---


@router.get("/vendors", response_model=Page[VendorRead])
def list_vendors(
    db: DbSession,
    company: CurrentCompany,
    page: PageParams,
    search: str | None = Query(default=None),
) -> Page[VendorRead]:
    query = select(Vendor).where(Vendor.company_code == company.code)
    if search:
        pattern = f"%{search}%"
        query = query.where(Vendor.name.ilike(pattern) | Vendor.code.ilike(pattern))
    query = query.order_by(Vendor.name)

    rows, total = paginate(db, query, page)
    return Page[VendorRead](
        items=[VendorRead.model_validate(row) for row in rows],
        meta=PageMeta(total=total, limit=page.limit, offset=page.offset),
    )


@router.get("/vendors/{vendor_id}", response_model=VendorRead)
def read_vendor(vendor_id: int, db: DbSession, company: CurrentCompany) -> Vendor:
    vendor = db.scalar(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.company_code == company.code)
    )
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.post("/vendors", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
def create_vendor(
    payload: VendorCreate, db: DbSession, user: Buyer, company: CurrentCompany
) -> Vendor:
    existing = db.scalar(
        select(Vendor).where(Vendor.company_code == company.code, Vendor.code == payload.code)
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Vendor code '{payload.code}' already exists")

    vendor = Vendor(company_code=company.code, **payload.model_dump())
    db.add(vendor)
    db.flush()

    activity.record(
        db,
        company_code=company.code,
        actor=user,
        entity="vendor",
        action="created",
        entity_id=vendor.id,
        summary=f"Created vendor {vendor.code}",
    )
    db.commit()
    db.refresh(vendor)
    return vendor


@router.patch("/vendors/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: int,
    payload: VendorUpdate,
    db: DbSession,
    user: Buyer,
    company: CurrentCompany,
) -> Vendor:
    vendor = db.scalar(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.company_code == company.code)
    )
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)

    db.commit()
    db.refresh(vendor)
    return vendor