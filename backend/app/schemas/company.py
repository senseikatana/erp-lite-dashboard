"""Company schemas."""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import ORMModel


class CompanyRead(ORMModel):
    code: str
    name: str
    currency: str
    locale: str
    default_language: str
    quality_check_required: bool
    modules_enabled: list[str] = Field(default_factory=list)


class CompanyUpdate(ORMModel):
    name: str | None = None
    currency: str | None = None
    locale: str | None = None
    default_language: str | None = None
    quality_check_required: bool | None = None
    modules_enabled: list[str] | None = None