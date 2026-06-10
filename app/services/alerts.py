"""Real-time reputation risk alerting.

Alerts are persisted, then best-effort delivered to a Slack/Discord-compatible
webhook if configured. Delivery failure never blocks the pipeline.
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Alert, Organization, Review
from app.schemas import ReviewAnalysis

logger = logging.getLogger("resona.alerts")


def raise_alert(db: Session, org: Organization, review: Review, analysis: ReviewAnalysis) -> Alert:
    message = (
        f"[{analysis.risk_level.value.upper()}] {org.name}: "
        f"{analysis.summary} "
        f"(reasons: {'; '.join(analysis.risk_reasons) or 'unspecified'}) "
        f"— review #{review.id} on {review.platform}"
    )
    alert = Alert(
        organization_id=org.id,
        review_id=review.id,
        level=analysis.risk_level,
        message=message,
    )
    db.add(alert)
    db.flush()

    alert.delivered = _deliver(message)
    return alert


def _deliver(message: str) -> bool:
    url = get_settings().resona_alert_webhook_url
    if not url:
        return False
    try:
        httpx.post(url, json={"text": message, "content": message}, timeout=5.0)
        return True
    except httpx.HTTPError as exc:
        logger.error("Alert webhook delivery failed: %s", exc)
        return False
