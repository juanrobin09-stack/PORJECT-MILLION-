"""Background worker: review polling + weekly insight scheduling.

Run alongside the API:  python -m app.worker

Two jobs:
1. poll_all_locations — every POLL_INTERVAL_MINUTES, pull new reviews from every
   configured connector for every location and push them through the pipeline.
2. weekly_insights — once a week, generate the executive report for every org.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select

from app.config import get_settings
from app.connectors import ALL_CONNECTORS
from app.database import SessionLocal, init_db
from app.models import Location, Organization, Review
from app.services import insights as insight_service
from app.services import pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("resona.worker")


def poll_all_locations() -> None:
    db = SessionLocal()
    try:
        connectors = [cls() for cls in ALL_CONNECTORS]
        active = [c for c in connectors if c.is_configured()]
        if not active:
            logger.info("No connectors configured; relying on webhook ingestion only")
            return

        for location in db.scalars(select(Location)).all():
            for connector in active:
                platform_id = (location.platform_ids or {}).get(connector.platform)
                if not platform_id:
                    continue
                last = db.scalar(
                    select(Review.review_created_at)
                    .where(
                        Review.location_id == location.id,
                        Review.platform == connector.platform,
                    )
                    .order_by(Review.review_created_at.desc())
                    .limit(1)
                )
                try:
                    raw_reviews = connector.fetch_reviews(platform_id, since=last)
                except Exception:
                    logger.exception(
                        "Connector %s failed for location %s", connector.platform, location.id
                    )
                    continue

                for raw in raw_reviews:
                    exists = db.scalar(
                        select(Review.id).where(
                            Review.platform == connector.platform,
                            Review.external_id == raw.external_id,
                        )
                    )
                    if exists:
                        continue
                    review = Review(
                        location_id=location.id,
                        platform=connector.platform,
                        external_id=raw.external_id,
                        author=raw.author,
                        rating=raw.rating,
                        text=raw.text,
                        review_created_at=raw.created_at,
                    )
                    db.add(review)
                    db.commit()
                    db.refresh(review)
                    try:
                        pipeline.process_review(db, review)
                    except Exception:
                        logger.exception("Pipeline failed for review %s", review.id)
    finally:
        db.close()


def weekly_insights() -> None:
    db = SessionLocal()
    try:
        for org in db.scalars(select(Organization)).all():
            try:
                report = insight_service.generate_weekly_report(db, org)
                if report:
                    logger.info("Weekly report %s generated for org %s", report.id, org.id)
            except Exception:
                logger.exception("Insight generation failed for org %s", org.id)
    finally:
        db.close()


def main() -> None:
    settings = get_settings()
    init_db()
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        poll_all_locations,
        "interval",
        minutes=settings.poll_interval_minutes,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.add_job(
        weekly_insights,
        "cron",
        day_of_week=settings.insights_weekday,
        hour=settings.insights_hour_utc,
    )
    logger.info(
        "Resona worker started (poll every %s min, insights weekly)",
        settings.poll_interval_minutes,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
