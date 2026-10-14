"""Customer and vendor schemas."""

from __future__ import annotations

from pydantic import EmailStr, Field

from app.schemas.common import ORMModel


class CustomerRead(ORMModel):
    id: int
    code: str
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str
    tax_id: str | None = None


class CustomerCreate(ORMModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str = "Spain"
    tax_id: str | None = None


class CustomerUpdate(ORMModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    tax_id: str | None = None


class VendorRead(ORMModel):
    id: int
    code: str
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    lead_time_days: int
    quality_rating: float


class VendorCreate(ORMModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None
    phone: str | None = None
    lead_time_days: int = Field(default=7, ge=0)
    quality_rating: float = Field(default=5.0, ge=0, le=5)


class VendorUpdate(ORMModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    lead_time_days: int | None = Field(default=None, ge=0)
    quality_rating: float | None = Field(default=None, ge=0, le=5)