"""Activity log writer.

Every state change in the application goes through ``record``. That is the
whole point: if a code path mutates business data without logging, the KPI
calculations silently under-report and the audit trail has holes.

The writer never commits. Callers own the transaction so a failure to log
cannot leave a committed change unrecorded.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.activity import ActivityEvent
from app.models.user import User


def record(
    db: Session,
    *,
    company_code: str,
    actor: User,
    entity: str,
    action: str,
    entity_id: int | None = None,
    summary: str | None = None,
    payload: dict[str, Any] | None = None,
) -> ActivityEvent:
    """Append one event to the activity log.

    Args:
        db: Active session. The event is flushed but not committed.
        company_code: Tenant the event belongs to.
        actor: User who caused the change.
        entity: Entity type, e.g. ``sales_order``.
        action: What happened, e.g. ``status_changed``.
        entity_id: Primary key of the affected row.
        summary: Short human-readable description for the activity feed.
        payload: Structured detail, typically the before/after values.
    """
    event = ActivityEvent(
        company_code=company_code,
        actor_id=actor.id,
        actor_username=actor.username,
        entity=entity,
        entity_id=entity_id,
        action=action,
        summary=summary,
        payload=payload,
    )
    db.add(event)
    db.flush()
    return event