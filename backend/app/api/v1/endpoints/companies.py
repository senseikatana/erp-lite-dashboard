"""Company endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import Administrator, CurrentCompany, CurrentUser, DbSession
from app.models.company import Company
from app.models.user import Role
from app.schemas.company import CompanyRead, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def list_companies(db: DbSession, user: CurrentUser) -> list[Company]:
    """List the companies the caller may operate in.

    Administrators see every registered company.
    """
    if user.role == Role.ADMIN:
        return list(db.scalars(select(Company).order_by(Company.code)).all())

    return list(user.companies)


@router.get("/current", response_model=CompanyRead)
def read_current_company(company: CurrentCompany) -> Company:
    """Return the company resolved for this request.

    Useful for the client to pick up currency, locale and enabled modules
    without hardcoding them.
    """
    return company


@router.patch("/current", response_model=CompanyRead)
def update_current_company(
    payload: CompanyUpdate, db: DbSession, user: Administrator, company: CurrentCompany
) -> Company:
    """Update company settings. Administrators only."""

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)
    return company