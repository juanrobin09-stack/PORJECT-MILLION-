"""Reputation module API: brand voice + the reply approval workflow.

The first vertical module on the platform. It owns no pipeline of its own —
drafts are produced by the `draft_reply` automation action; this router is the
human-in-the-loop surface.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from sona.api.schemas import BrandVoiceOut, BrandVoiceUpsert, ReplyDraftEdit, ReplyDraftOut
from sona.auth import current_org
from sona.database import get_db
from sona.models import BrandVoice, Organization, ReplyDraft, ReplyStatus, Signal

router = APIRouter(prefix="/reputation", tags=["reputation"])


@router.put("/brand-voice", response_model=BrandVoiceOut)
def upsert_brand_voice(
    body: BrandVoiceUpsert,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    voice = db.scalars(
        select(BrandVoice).where(BrandVoice.organization_id == org.id)
    ).first()
    if voice is None:
        voice = BrandVoice(organization_id=org.id)
        db.add(voice)
    for field, value in body.model_dump().items():
        setattr(voice, field, value)
    db.commit()
    db.refresh(voice)
    return voice


@router.get("/brand-voice", response_model=BrandVoiceOut | None)
def get_brand_voice(org: Organization = Depends(current_org), db: Session = Depends(get_db)):
    return db.scalars(select(BrandVoice).where(BrandVoice.organization_id == org.id)).first()


def _owned_draft(draft_id: int, org: Organization, db: Session) -> ReplyDraft:
    draft = db.get(ReplyDraft, draft_id)
    if draft is None or draft.signal.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.get("/drafts", response_model=list[ReplyDraftOut])
def list_drafts(
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
    status: ReplyStatus | None = None,
    limit: int = 50,
    offset: int = 0,
):
    query = (
        select(ReplyDraft)
        .join(Signal, ReplyDraft.signal_id == Signal.id)
        .where(Signal.organization_id == org.id)
    )
    if status is not None:
        query = query.where(ReplyDraft.status == status)
    return db.scalars(
        query.order_by(ReplyDraft.generated_at.desc()).limit(min(limit, 200)).offset(offset)
    ).all()


@router.patch("/drafts/{draft_id}", response_model=ReplyDraftOut)
def edit_draft(
    draft_id: int,
    body: ReplyDraftEdit,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    draft = _owned_draft(draft_id, org, db)
    if draft.status == ReplyStatus.published:
        raise HTTPException(status_code=409, detail="Cannot edit a published reply")
    draft.text = body.text
    draft.status = ReplyStatus.pending_approval
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/drafts/{draft_id}/approve", response_model=ReplyDraftOut)
def approve_draft(
    draft_id: int,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    draft = _owned_draft(draft_id, org, db)
    if draft.status not in (ReplyStatus.pending_approval, ReplyStatus.rejected):
        raise HTTPException(status_code=409, detail=f"Cannot approve from {draft.status.value}")
    draft.status = ReplyStatus.approved
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/drafts/{draft_id}/reject", response_model=ReplyDraftOut)
def reject_draft(
    draft_id: int,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    draft = _owned_draft(draft_id, org, db)
    draft.status = ReplyStatus.rejected
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/drafts/{draft_id}/mark-published", response_model=ReplyDraftOut)
def mark_published(
    draft_id: int,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    draft = _owned_draft(draft_id, org, db)
    if draft.status != ReplyStatus.approved:
        raise HTTPException(status_code=409, detail="Only approved replies can be published")
    draft.status = ReplyStatus.published
    draft.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(draft)
    return draft
