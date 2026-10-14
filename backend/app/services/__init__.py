"""Business logic services.

Endpoints stay thin: they resolve the actor, delegate to a service, and map
domain errors to HTTP status codes. Anything that encodes a business rule
lives here so it can be unit tested without a request.
"""

from app.services import activity, demand_service, kpi_service, purchasing_service, sales_service

__all__ = [
    "activity",
    "demand_service",
    "kpi_service",
    "purchasing_service",
    "sales_service",
]