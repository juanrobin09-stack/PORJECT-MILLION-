"""Weekly insight report generation.

Aggregates the trailing 7 days of analyzed reviews into a compact digest
(controls token spend), sends it to the insights model, and persists the
structured report.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.engine import AIEngine, get_engine
from app.models import InsightReport, Location, Organization, Review

logger = logging.getLogger("resona.insights")


def build_digest(db: Session, org: Organization, start: datetime, end: datetime) -> str | None:
    rows = db.execute(
        select(Review, Location.name)
        .join(Location, Review.location_id == Location.id)
        .where(
            Location.organization_id == org.id,
            Review.ingested_at >= start,
            Review.ingested_at < end,
            Review.analyzed_at.is_not(None),
        )
        .order_by(Review.ingested_at)
    ).all()
    if not rows:
        return None

    topic_counts: Counter[str] = Counter()
    lines: list[str] = []
    for review, location_name in rows:
        topic_counts.update(review.topics or [])
        lines.append(
            f"- [{location_name}] {review.rating or '?'}/5 "
            f"{review.sentiment.value if review.sentiment else '?'} "
            f"(score {review.sentiment_score:+.2f}) "
            f"risk={review.risk_level.value} topics={','.join(review.topics or [])} :: "
            f"{(review.text or '')[:240]}"
        )

    header = (
        f"{len(rows)} reviews this period. "
        f"Top topics: {', '.join(f'{t} (x{c})' for t, c in topic_counts.most_common(10))}\n"
    )
    return header + "\n".join(lines)


def generate_weekly_report(
    db: Session, org: Organization, engine: AIEngine | None = None
) -> InsightReport | None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)

    digest = build_digest(db, org, start, end)
    if digest is None:
        logger.info("Org %s: no analyzed reviews this week, skipping report", org.id)
        return None

    previous = db.scalars(
        select(InsightReport)
        .where(InsightReport.organization_id == org.id)
        .order_by(InsightReport.created_at.desc())
        .limit(1)
    ).first()

    engine = engine or get_engine()
    insights = engine.weekly_insights(
        review_digest=digest,
        baseline_summary=previous.summary if previous else "",
    )

    report = InsightReport(
        organization_id=org.id,
        period_start=start,
        period_end=end,
        summary=insights.executive_summary,
        data=insights.model_dump(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
