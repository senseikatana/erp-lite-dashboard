"""Business partners: customers and vendors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CompanyScopedMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.sales import SalesOrder


class Customer(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(180))
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(80))
    postal_code: Mapped[str | None] = mapped_column(String(10))
    country: Mapped[str] = mapped_column(String(60), default="Spain", nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(30))

    company: Mapped[Company] = relationship(back_populates="customers")
    orders: Mapped[list[SalesOrder]] = relationship(back_populates="customer")


class Vendor(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(180))
    phone: Mapped[str | None] = mapped_column(String(30))

    # Planning inputs. Lead time feeds the demand worksheet, quality rating
    # feeds purchase suggestions.
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    quality_rating: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)

    company: Mapped[Company] = relationship(back_populates="vendors")


# Monetary values are stored as fixed-precision decimals rather than floats.
# 0.1 + 0.2 is not 0.3 in binary floating point, and an ERP that reports totals
# a cent off on every invoice is an ERP nobody trusts.
Money = Numeric(14, 2)
Quantity = Numeric(14, 3)