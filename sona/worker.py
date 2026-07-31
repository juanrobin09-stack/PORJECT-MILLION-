"""Background worker: connector polling + nightly benchmark recomputation.

Run alongside the API:  python -m sona.worker
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from sona import benchmarks, pipeline
from sona.config import get_settings
from sona.connectors import ALL_CONNECTORS
from sona.database import SessionLocal, init_db
from sona.models import Signal, Source

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("sona.worker")


def poll_sources() -> None:
    db = SessionLocal()
    try:
        connectors = {c.source_kind: c for c in (cls() for cls in ALL_CONNECTORS) if c.is_configured()}
        if not connectors:
            logger.info("No connectors configured; ingest API only")
            return

        for source in db.scalars(select(Source)).all():
            connector = connectors.get(source.kind)
            if connector is None:
                continue
            last = db.scalar(
                select(Signal.occurred_at)
                .where(Signal.source_id == source.id)
                .order_by(Signal.occurred_at.desc())
                .limit(1)
            )
            try:
                raw_signals = connector.fetch(source.config or {}, since=last)
            except Exception:
                logger.exception("Connector %s failed for source %s", source.kind, source.id)
                continue

            for raw in raw_signals:
                exists = db.scalar(
                    select(Signal.id).where(
                        Signal.source_id == source.id, Signal.external_id == raw.external_id
                    )
                )
                if exists:
                    continue
                signal = Signal(
                    organization_id=source.organization_id,
                    source_id=source.id,
                    external_id=raw.external_id,
                    kind=raw.kind,
                    author=raw.author,
                    content=raw.content,
                    rating=raw.rating,
                    nps_score=raw.nps_score,
                    meta=raw.meta,
                    occurred_at=raw.occurred_at,
                )
                db.add(signal)
                db.commit()
                db.refresh(signal)
                try:
                    pipeline.process_signal(db, signal)
                except Exception:
                    logger.exception("Pipeline failed for signal %s", signal.id)
    finally:
        db.close()


def recompute_benchmarks() -> None:
    db = SessionLocal()
    try:
        benchmarks.compute_benchmarks(db)
    except Exception:
        logger.exception("Benchmark computation failed")
    finally:
        db.close()


def main() -> None:
    settings = get_settings()
    init_db()
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        poll_sources,
        "interval",
        minutes=settings.poll_interval_minutes,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.add_job(recompute_benchmarks, "cron", hour=settings.benchmark_hour_utc)
    logger.info(
        "Sona worker started (poll every %s min, benchmarks daily at %02d:00 UTC)",
        settings.poll_interval_minutes,
        settings.benchmark_hour_utc,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
