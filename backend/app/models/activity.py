"""Append-only activity event log.

This table is the reason the dashboard can show measured KPIs instead of
placeholder numbers. A counter such as ``qty_picked`` tells you *how much* was
picked but never *when*, so "picks per hour" is unanswerable without a record
of the event itself.

The same log serves as the audit trail: who changed what, and when.

Design notes:

* Rows are append-only. There is no ``updated_at`` on purpose.
* ``payload`` holds the before/after detail as JSON so the schema does not
  have to grow every time a workflow adds a field.
* ``occurred_at`` is stored in UTC. Conversion to the company's locale happens
  in the presentation layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    company_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("companies.code", ondelete="CASCADE"), nullable=False
    )

    # The actor is denormalised on purpose. If a user is later renamed or
    # deactivated the historical trail must keep showing who did the work.
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_username: Mapped[str] = mapped_column(String(60), nullable=False)

    # e.g. "sales_order", "purchase_order", "item"
    entity: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # e.g. "created", "status_changed", "received", "qc_approved"
    action: Mapped[str] = mapped_column(String(50), nullable=False)

    # Short human-readable line shown in the UI, already localised by the client.
    summary: Mapped[str | None] = mapped_column(Text)

    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        # The dashboard queries recent events for one company, newest first.
        Index("ix_activity_company_time", "company_code", "occurred_at"),
        # Rate calculations bucket events by entity type over a time window.
        Index("ix_activity_entity_action_time", "entity", "action", "occurred_at"),
    )