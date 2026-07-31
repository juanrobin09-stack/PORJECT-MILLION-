"""Usage metering: one enriched signal = one billable unit, monthly reset."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sona.models import PLAN_SIGNAL_QUOTA, Organization, UsageRecord


def _period_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def signals_used(db: Session, org: Organization) -> int:
    return db.scalar(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.organization_id == org.id,
            UsageRecord.kind == "signal_enriched",
            UsageRecord.created_at >= _period_start(),
        )
    ) or 0


def quota_for(org: Organization) -> int | None:
    return PLAN_SIGNAL_QUOTA[org.plan]


def has_quota(db: Session, org: Organization) -> bool:
    quota = quota_for(org)
    if quota is None:
        return True
    return signals_used(db, org) < quota
