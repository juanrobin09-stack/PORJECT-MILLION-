from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_org
from app.database import SessionLocal, get_db
from app.models import Location, Organization, Review, RiskLevel, Sentiment
from app.routers.locations import get_owned_location
from app.schemas import ReviewIngest, ReviewOut
from app.services import pipeline

router = APIRouter(tags=["reviews"])


def _process_in_background(review_id: int) -> None:
    db = SessionLocal()
    try:
        review = db.get(Review, review_id)
        if review is not None:
            pipeline.process_review(db, review)
    finally:
        db.close()


@router.post("/reviews/ingest", response_model=ReviewOut, status_code=202)
def ingest_review(
    body: ReviewIngest,
    background: BackgroundTasks,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    """Ingest a single review. Idempotent on (platform, external_id).

    Analysis and response drafting run asynchronously; poll the review or the
    responses endpoint for results.
    """
    get_owned_location(body.location_id, org, db)

    existing = db.scalars(
        select(Review).where(
            Review.platform == body.platform, Review.external_id == body.external_id
        )
    ).first()
    if existing is not None:
        return existing

    review = Review(
        location_id=body.location_id,
        platform=body.platform,
        external_id=body.external_id,
        author=body.author,
        rating=body.rating,
        text=body.text,
        **({"review_created_at": body.review_created_at} if body.review_created_at else {}),
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    background.add_task(_process_in_background, review.id)
    return review


@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
    location_id: int | None = None,
    sentiment: Sentiment | None = None,
    risk_level: RiskLevel | None = None,
    limit: int = 50,
    offset: int = 0,
):
    query = (
        select(Review)
        .join(Location, Review.location_id == Location.id)
        .where(Location.organization_id == org.id)
    )
    if location_id is not None:
        query = query.where(Review.location_id == location_id)
    if sentiment is not None:
        query = query.where(Review.sentiment == sentiment)
    if risk_level is not None:
        query = query.where(Review.risk_level == risk_level)
    query = query.order_by(Review.ingested_at.desc()).limit(min(limit, 200)).offset(offset)
    return db.scalars(query).all()


@router.get("/reviews/{review_id}", response_model=ReviewOut)
def get_review(
    review_id: int,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    review = db.get(Review, review_id)
    if review is None or review.location.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Review not found")
    return review
