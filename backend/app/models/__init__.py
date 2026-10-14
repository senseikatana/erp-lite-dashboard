"""ORM models.

Importing this package registers every table on ``Base.metadata`` before
``create_all`` or an Alembic autogenerate runs.
"""

from app.models.activity import ActivityEvent
from app.models.base import Base, CompanyScopedMixin, TimestampMixin, utcnow
from app.models.company import Company
from app.models.demand import DemandAction, DemandLine, DemandSource
from app.models.item import Item
from app.models.partner import Customer, Vendor
from app.models.purchasing import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    QualityStatus,
)
from app.models.routing import RouteStatus, ShipmentRoute
from app.models.sales import SalesOrder, SalesOrderLine, SalesOrderStatus
from app.models.user import Role, User, UserCompanyAccess

__all__ = [
    "ActivityEvent",
    "Base",
    "Company",
    "CompanyScopedMixin",
    "Customer",
    "DemandAction",
    "DemandLine",
    "DemandSource",
    "Item",
    "PurchaseOrder",
    "PurchaseOrderLine",
    "PurchaseOrderStatus",
    "QualityStatus",
    "Role",
    "RouteStatus",
    "SalesOrder",
    "SalesOrderLine",
    "SalesOrderStatus",
    "ShipmentRoute",
    "TimestampMixin",
    "User",
    "UserCompanyAccess",
    "Vendor",
    "utcnow",
]