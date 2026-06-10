"""Ask your customers anything — natural-language synthesis over signals.

This endpoint is the clearest expression of the data moat: the more channels a
customer routes through Sona, the better the answers get, and nothing else in
their stack can answer at all.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from sona.api.schemas import AskRequest, AskResponse
from sona.auth import current_org
from sona.config import get_settings
from sona.database import get_db
from sona.intelligence.engine import get_engine
from sona.models import Organization, Signal

router = APIRouter(tags=["ask"])


def build_digest(signals: list[Signal]) -> str:
    lines = []
    for s in signals:
        score = f"{s.sentiment_score:+.2f}" if s.sentiment_score is not None else "?"
        lines.append(
            f"[#{s.id}] kind={s.kind.value} rating={s.rating or 'n/a'} nps={s.nps_score if s.nps_score is not None else 'n/a'} "
            f"sentiment={s.sentiment.value if s.sentiment else '?'}({score}) "
            f"intent={s.intent.value if s.intent else '?'} risk={s.risk_level.value} "
            f"topics={','.join(s.topics or [])} :: {(s.content or '')[:220]}"
        )
    return f"{len(signals)} signals.\n" + "\n".join(lines)


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    org: Organization = Depends(current_org),
    db: Session = Depends(get_db),
):
    if not get_settings().ai_enabled:
        raise HTTPException(status_code=503, detail="AI is not configured on this deployment")

    since = datetime.now(timezone.utc) - timedelta(days=body.days)
    query = select(Signal).where(
        Signal.organization_id == org.id,
        Signal.enriched_at.is_not(None),
        Signal.ingested_at >= since,
    )
    if body.kind is not None:
        query = query.where(Signal.kind == body.kind)
    signals = list(
        db.scalars(query.order_by(Signal.ingested_at.desc()).limit(body.max_signals)).all()
    )
    if not signals:
        raise HTTPException(
            status_code=422, detail="No enriched signals in the selected window"
        )

    answer = get_engine().synthesize(body.question, build_digest(signals))
    own_ids = {s.id for s in signals}
    return AskResponse(
        answer=answer.answer,
        evidence_signal_ids=[i for i in answer.evidence_signal_ids if i in own_ids],
        confidence=answer.confidence,
        caveats=answer.caveats,
        signals_considered=len(signals),
    )
