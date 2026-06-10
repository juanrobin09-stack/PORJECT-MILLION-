"""The Sona pipeline: ingest -> enrich -> automate -> meter.

Every signal from every channel flows through `process_signal`. Idempotent per
signal; called by the ingest API (background task) and the connector worker.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from sona.actions import engine as actions
from sona.config import get_settings
from sona.intelligence.engine import IntelligenceEngine, get_engine
from sona.models import Organization, Signal, UsageRecord
from sona.usage import has_quota

logger = logging.getLogger("sona.pipeline")


def process_signal(
    db: Session, signal: Signal, engine: IntelligenceEngine | None = None
) -> Signal:
    settings = get_settings()
    org = db.get(Organization, signal.organization_id)

    if signal.enriched_at is not None:
        return signal  # idempotent

    if not settings.ai_enabled and engine is None:
        logger.warning("AI disabled (no ANTHROPIC_API_KEY); signal %s stored raw", signal.id)
        return signal

    # Quota: enrichment is the billable unit. Over quota, signals are stored
    # raw (never dropped) and enriched retroactively on upgrade.
    if not has_quota(db, org):
        logger.info("Org %s over quota; signal %s stored raw", org.id, signal.id)
        return signal

    engine = engine or get_engine()

    enrichment, unmapped = engine.enrich(
        {
            "kind": signal.kind.value,
            "rating": signal.rating,
            "nps_score": signal.nps_score,
            "author_name": (signal.author or {}).get("name", "Anonymous"),
            "content": signal.content,
        }
    )

    signal.sentiment = enrichment.sentiment
    signal.sentiment_score = enrichment.sentiment_score
    signal.language = enrichment.language
    signal.intent = enrichment.intent
    signal.urgency = enrichment.urgency
    signal.risk_level = enrichment.risk_level
    signal.risk_reasons = enrichment.risk_reasons
    signal.churn_risk = enrichment.churn_risk
    signal.topics = enrichment.topics
    signal.raw_topics = unmapped
    signal.summary = enrichment.summary
    signal.enriched_at = datetime.now(timezone.utc)

    db.add(UsageRecord(organization_id=org.id, kind="signal_enriched"))
    db.commit()

    actions.run_automations(db, org, signal, engine)
    db.refresh(signal)
    return signal
