"""Aggregates every v1 endpoint module into a single router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    companies,
    dashboard,
    partners,
    planning,
    purchases,
    sales,
    warehouse,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(dashboard.router)
api_router.include_router(sales.router)
api_router.include_router(purchases.router)
api_router.include_router(warehouse.router)
api_router.include_router(partners.router)
api_router.include_router(planning.router)