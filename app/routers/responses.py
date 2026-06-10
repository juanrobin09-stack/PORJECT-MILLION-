from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_org
from app.database import get_db
from app.models import (
    Location,
    Organization,
    ResponseStatus,
    Review,
    ReviewResponse,
)
from app.schemas import ResponseEdit, ResponseOut

router = APIRouter(tags=["responses"])


def _owned_response(response_id: int, org: Organization, db: Session) -> ReviewResponse:
    resp = db.get(ReviewResponse, response_id)
    if resp is None or resp.review.location.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Response not found")
    return resp


@router.get("/responses", response_model=list[ResponseOut])
def list_responses(
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
    status: ResponseStatus | None = None,
    limit: int = 50,
    offset: int = 0,
):
    query = (
        select(ReviewResponse)
        .join(Review, ReviewResponse.review_id == Review.id)
        .join(Location, Review.location_id == Location.id)
        .where(Location.organization_id == org.id)
    )
    if status is not None:
        query = query.where(ReviewResponse.status == status)
    query = query.order_by(ReviewResponse.generated_at.desc()).limit(min(limit, 200)).offset(offset)
    return db.scalars(query).all()


@router.post("/responses/{response_id}/approve", response_model=ResponseOut)
def approve_response(
    response_id: int,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    resp = _owned_response(response_id, org, db)
    if resp.status not in (ResponseStatus.pending_approval, ResponseStatus.rejected):
        raise HTTPException(status_code=409, detail=f"Cannot approve from status {resp.status.value}")
    resp.status = ResponseStatus.approved
    db.commit()
    db.refresh(resp)
    return resp


@router.post("/responses/{response_id}/reject", response_model=ResponseOut)
def reject_response(
    response_id: int,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    resp = _owned_response(response_id, org, db)
    resp.status = ResponseStatus.rejected
    db.commit()
    db.refresh(resp)
    return resp


@router.patch("/responses/{response_id}", response_model=ResponseOut)
def edit_response(
    response_id: int,
    body: ResponseEdit,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    """Edit the draft text (resets to pending_approval)."""
    resp = _owned_response(response_id, org, db)
    if resp.status == ResponseStatus.published:
        raise HTTPException(status_code=409, detail="Cannot edit a published response")
    resp.text = body.text
    resp.status = ResponseStatus.pending_approval
    db.commit()
    db.refresh(resp)
    return resp


@router.post("/responses/{response_id}/mark-published", response_model=ResponseOut)
def mark_published(
    response_id: int,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    """Mark an approved response as published.

    In production the publisher worker calls this after pushing the reply to the
    platform API; draft_only customers call it after publishing manually.
    """
    resp = _owned_response(response_id, org, db)
    if resp.status != ResponseStatus.approved:
        raise HTTPException(status_code=409, detail="Only approved responses can be published")
    resp.status = ResponseStatus.published
    resp.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(resp)
    return resp
