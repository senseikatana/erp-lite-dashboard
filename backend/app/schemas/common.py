"""Shared schema helpers."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

T = TypeVar("T")


class Schema(BaseModel):
    """Base class for request/response models.

    ``from_attributes`` lets a schema be constructed directly from an ORM
    instance, which removes the DTO mapping boilerplate from every endpoint.
    """

    model_config = ConfigDict(from_attributes=True)


class ORMModel(Schema):
    """Schema that can also be populated from an ORM row."""


# Domain values stay Decimal end-to-end. JSON has no decimal type, so they are
# serialised as numbers at the API boundary only.
MoneyOut = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]
QuantityOut = MoneyOut


class PageMeta(Schema):
    """Pagination envelope metadata."""

    total: int = Field(description="Total rows matching the query, before pagination")
    limit: int
    offset: int


class Page(Schema, Generic[T]):
    """A page of results plus its pagination metadata."""

    items: list[T]
    meta: PageMeta


class Message(Schema):
    """Simple acknowledgement payload."""

    message: str