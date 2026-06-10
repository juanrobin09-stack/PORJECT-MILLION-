"""The core Resona pipeline: ingest -> analyze -> draft -> route.

Every review flows through `process_review`. The pipeline is synchronous and
idempotent per review; the worker and the ingest endpoint both call it.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.engine import AIEngine, get_engine
from app.config import get_settings
from app.models import (
    BrandVoice,
    Location,
    Organization,
    ResponseMode,
    ResponseStatus,
    Review,
    ReviewResponse,
    RiskLevel,
    Sentiment,
    UsageRecord,
)
from app.services import alerts as alert_service
from app.services import usage as usage_service

logger = logging.getLogger("resona.pipeline")

# Reviews at or above this risk level are never auto-published.
AUTO_PUBLISH_MAX_RISK = {RiskLevel.none, RiskLevel.low}


def _voice_dict(voice: BrandVoice | None) -> dict:
    if voice is None:
        return {}
    return {
        "tone": voice.tone,
        "sign_off": voice.sign_off,
        "language": voice.language,
        "forbidden_phrases": voice.forbidden_phrases,
        "talking_points": voice.talking_points,
        "offer_compensation": voice.offer_compensation,
        "max_words": voice.max_words,
    }


def process_review(db: Session, review: Review, engine: AIEngine | None = None) -> Review:
    """Analyze a review, draft a response, and route it per the location's mode.

    Degrades gracefully: with no API key configured (dev/demo), the review is
    stored unanalyzed and no draft is produced.
    """
    settings = get_settings()
    location = db.get(Location, review.location_id)
    org = db.get(Organization, location.organization_id)

    if not settings.ai_enabled and engine is None:
        logger.warning("AI disabled (no ANTHROPIC_API_KEY); review %s stored raw", review.id)
        return review

    engine = engine or get_engine()

    # 1. Analyze
    analysis = engine.analyze_review(
        {
            "platform": review.platform,
            "rating": review.rating,
            "author": review.author,
            "text": review.text,
        }
    )
    review.sentiment = analysis.sentiment
    review.sentiment_score = analysis.sentiment_score
    review.topics = analysis.topics
    review.risk_level = analysis.risk_level
    review.risk_reasons = analysis.risk_reasons
    review.churn_risk = analysis.churn_risk
    review.analyzed_at = datetime.now(timezone.utc)

    # 2. Alert on risk before anything else — owners must hear about a
    #    health/safety claim from Resona, not from a journalist.
    if analysis.risk_level in (RiskLevel.high, RiskLevel.critical):
        alert_service.raise_alert(db, org, review, analysis)

    # 3. Quota check — analysis is always free, drafting is the billable unit.
    if not usage_service.has_quota(db, org):
        logger.info("Org %s over quota; skipping draft for review %s", org.id, review.id)
        db.commit()
        return review

    # 4. Draft
    voice = _voice_dict(org.brand_voice)
    draft = engine.draft_response(
        {
            "platform": review.platform,
            "rating": review.rating,
            "author": review.author,
            "text": review.text,
        },
        analysis,
        voice,
    )

    # 5. Route per response mode + safety overrides
    status = ResponseStatus.pending_approval
    if (
        location.response_mode == ResponseMode.auto_publish
        and not draft.escalate_to_human
        and analysis.risk_level in AUTO_PUBLISH_MAX_RISK
        and analysis.sentiment in (Sentiment.positive, Sentiment.neutral)
    ):
        status = ResponseStatus.approved  # publisher picks up approved drafts

    db.add(
        ReviewResponse(
            review_id=review.id,
            text=draft.response_text,
            status=status,
            model=get_settings().resona_model_response,
        )
    )
    db.add(UsageRecord(organization_id=org.id, kind="ai_response"))
    db.commit()
    db.refresh(review)
    return review
