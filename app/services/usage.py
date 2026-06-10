"""Quota enforcement and usage metering.

The billable unit is one AI-drafted response. Quotas reset monthly and scale
with plan and location count (quota = per-location quota x active locations).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import PLAN_RESPONSE_QUOTA, Location, Organization, UsageRecord


def _period_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def responses_used(db: Session, org: Organization) -> int:
    return db.scalar(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.organization_id == org.id,
            UsageRecord.kind == "ai_response",
            UsageRecord.created_at >= _period_start(),
        )
    ) or 0


def quota_for(db: Session, org: Organization) -> int | None:
    per_location = PLAN_RESPONSE_QUOTA[org.plan]
    if per_location is None:
        return None
    location_count = db.scalar(
        select(func.count(Location.id)).where(Location.organization_id == org.id)
    ) or 0
    return per_location * max(location_count, 1)


def has_quota(db: Session, org: Organization) -> bool:
    quota = quota_for(db, org)
    if quota is None:
        return True
    return responses_used(db, org) < quota
