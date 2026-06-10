"""Cross-tenant benchmarks — the network effect, built privacy-first.

Because every tenant's signals are normalized onto one canonical taxonomy,
Sona can compute per-(industry, topic, month) aggregates across tenants:
average sentiment and the share of negative signals. No tenant data crosses
the boundary — only aggregates with k-anonymity (a segment is published only
when >= SONA_BENCHMARK_MIN_ORGS distinct organizations contribute).

This compounds: every new customer makes the benchmarks better for every
existing customer, and the benchmarks cannot be replicated without the
customer base. It is the reason Sona gets harder to compete with every month
it operates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sona.config import get_settings
from sona.models import BenchmarkStat, Organization, Sentiment, Signal

logger = logging.getLogger("sona.benchmarks")


def current_period(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def compute_benchmarks(db: Session, period: str | None = None) -> int:
    """Recompute aggregates for one period. Returns segments written.

    Aggregation is per (industry, topic): a signal tagged with three topics
    contributes to three segments.
    """
    period = period or current_period()

    rows = db.execute(
        select(
            Organization.industry,
            Organization.id,
            Signal.topics,
            Signal.sentiment,
            Signal.sentiment_score,
        )
        .join(Organization, Signal.organization_id == Organization.id)
        .where(
            Signal.enriched_at.is_not(None),
            func.strftime("%Y-%m", Signal.ingested_at) == period
            if db.bind.dialect.name == "sqlite"
            else func.to_char(Signal.ingested_at, "YYYY-MM") == period,
        )
    ).all()

    # segment -> {org_ids, scores, negatives}
    segments: dict[tuple[str, str], dict] = {}
    for industry, org_id, topics, sentiment, score in rows:
        for topic in topics or []:
            seg = segments.setdefault(
                (industry, topic), {"orgs": set(), "scores": [], "neg": 0, "n": 0}
            )
            seg["orgs"].add(org_id)
            seg["n"] += 1
            if score is not None:
                seg["scores"].append(score)
            if sentiment == Sentiment.negative:
                seg["neg"] += 1

    written = 0
    for (industry, topic), seg in segments.items():
        stat = db.scalars(
            select(BenchmarkStat).where(
                BenchmarkStat.industry == industry,
                BenchmarkStat.topic == topic,
                BenchmarkStat.period == period,
            )
        ).first()
        if stat is None:
            stat = BenchmarkStat(industry=industry, topic=topic, period=period)
            db.add(stat)
        stat.org_count = len(seg["orgs"])
        stat.signal_count = seg["n"]
        stat.avg_sentiment = sum(seg["scores"]) / len(seg["scores"]) if seg["scores"] else 0.0
        stat.negative_share = seg["neg"] / seg["n"] if seg["n"] else 0.0
        stat.computed_at = datetime.now(timezone.utc)
        written += 1

    db.commit()
    logger.info("Benchmarks computed for %s: %d segments", period, written)
    return written


def published_benchmarks(
    db: Session, industry: str, period: str | None = None, min_orgs: int | None = None
) -> list[BenchmarkStat]:
    """Segments visible to customers — k-anonymity enforced here, at read time."""
    period = period or current_period()
    min_orgs = min_orgs if min_orgs is not None else get_settings().sona_benchmark_min_orgs
    return list(
        db.scalars(
            select(BenchmarkStat)
            .where(
                BenchmarkStat.industry == industry,
                BenchmarkStat.period == period,
                BenchmarkStat.org_count >= min_orgs,
            )
            .order_by(BenchmarkStat.signal_count.desc())
        ).all()
    )
