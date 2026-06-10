from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from sona import pipeline
from sona.api.schemas import SignalIngest, SignalOut
from sona.auth import current_org
from sona.database import SessionLocal, get_db
from sona.models import (
    Intent,
    Organization,
    RiskLevel,
    Sentiment,
    Signal,
    SignalKind,
    Source,
)

router = APIRouter(tags=["signals"])


def _process_in_background(signal_id: int) -> None:
    db = SessionLocal()
    try:
        signal = db.get(Signal, signal_id)
        if signal is not None:
            pipeline.process_signal(db, signal)
    finally:
        db.close()


@router.post("/signals", response_model=SignalOut, status_code=202)
def ingest_signal(
    body: SignalIngest,
    background: BackgroundTasks,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    """Ingest one signal from any channel. Idempotent on (source_id, external_id).
    Enrichment and automations run asynchronously after the 202."""
    source = db.get(Source, body.source_id)
    if source is None or source.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Source not found")

    existing = db.scalars(
        select(Signal).where(
            Signal.source_id == body.source_id, Signal.external_id == body.external_id
        )
    ).first()
    if existing is not None:
        return existing

    signal = Signal(
        organization_id=org.id,
        source_id=body.source_id,
        external_id=body.external_id,
        kind=body.kind,
        author=body.author,
        content=body.content,
        rating=body.rating,
        nps_score=body.nps_score,
        meta=body.meta,
        **({"occurred_at": body.occurred_at} if body.occurred_at else {}),
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)

    background.add_task(_process_in_background, signal.id)
    return signal


@router.get("/signals", response_model=list[SignalOut])
def list_signals(
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
    source_id: int | None = None,
    kind: SignalKind | None = None,
    sentiment: Sentiment | None = None,
    intent: Intent | None = None,
    risk_level: RiskLevel | None = None,
    topic: str | None = None,
    churn_risk: bool | None = None,
    limit: int = 50,
    offset: int = 0,
):
    query = select(Signal).where(Signal.organization_id == org.id)
    if source_id is not None:
        query = query.where(Signal.source_id == source_id)
    if kind is not None:
        query = query.where(Signal.kind == kind)
    if sentiment is not None:
        query = query.where(Signal.sentiment == sentiment)
    if intent is not None:
        query = query.where(Signal.intent == intent)
    if risk_level is not None:
        query = query.where(Signal.risk_level == risk_level)
    if churn_risk is not None:
        query = query.where(Signal.churn_risk == churn_risk)
    rows = db.scalars(
        query.order_by(Signal.ingested_at.desc()).limit(min(limit, 200)).offset(offset)
    ).all()
    if topic is not None:  # JSON-list filter, applied in Python for portability
        rows = [s for s in rows if topic in (s.topics or [])]
    return rows


@router.get("/signals/{signal_id}", response_model=SignalOut)
def get_signal(
    signal_id: int,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    signal = db.get(Signal, signal_id)
    if signal is None or signal.organization_id != org.id:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal
