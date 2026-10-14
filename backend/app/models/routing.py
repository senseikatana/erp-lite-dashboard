"""Shipment routes."""

from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CompanyScopedMixin, TimestampMixin

if TYPE_CHECKING:
    pass


class RouteStatus(enum.StrEnum):
    PLANNED = "PLANNED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"


class ShipmentRoute(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    carrier: Mapped[str] = mapped_column(String(60), nullable=False)
    date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False, index=True)
    status: Mapped[RouteStatus] = mapped_column(
        Enum(RouteStatus, native_enum=False, length=20),
        default=RouteStatus.PLANNED,
        nullable=False,
    )
    stops: Mapped[int] = mapped_column(Integer, default=0, nullable=False)