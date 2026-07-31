"""The automation engine: declarative rules over enriched signals.

A rule is a list of AND-combined conditions on the canonical schema plus one
action. Because the schema is canonical, one rule works across every channel —
"negative review" and "detractor NPS verbatim" are the same condition language.

Actions:
- webhook     POST the enriched signal to a customer URL (their CRM, Slack,
              ticketing — Sona becomes the event source for their stack).
- alert       Persist an alert ActionRun and POST to the alert webhook in
              action_config (or org default).
- draft_reply Invoke the reputation module: Claude drafts a public reply,
              routed through the approval workflow.
- tag         Append tags to the signal's metadata (cheap routing primitive).

Safety invariant (code, not prompt): a draft for a signal at risk high/critical
or with the model's own escalate flag can never be auto-approved.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from sona.config import get_settings
from sona.intelligence.engine import IntelligenceEngine
from sona.models import (
    RISK_ORDER,
    ActionRun,
    Automation,
    BrandVoice,
    Organization,
    ReplyDraft,
    ReplyStatus,
    RiskLevel,
    Sentiment,
    Signal,
)

logger = logging.getLogger("sona.actions")

AUTO_APPROVE_MAX_RISK = {RiskLevel.none, RiskLevel.low}


# --- Condition evaluation ----------------------------------------------------

_FIELDS = {
    "kind": lambda s: s.kind.value if s.kind else None,
    "sentiment": lambda s: s.sentiment.value if s.sentiment else None,
    "sentiment_score": lambda s: s.sentiment_score,
    "intent": lambda s: s.intent.value if s.intent else None,
    "urgency": lambda s: s.urgency.value if s.urgency else None,
    "risk_level": lambda s: s.risk_level.value if s.risk_level else None,
    "churn_risk": lambda s: s.churn_risk,
    "rating": lambda s: s.rating,
    "nps_score": lambda s: s.nps_score,
    "topics": lambda s: s.topics or [],
    "language": lambda s: s.language,
}

_RISK_RANK = {level.value: i for i, level in enumerate(RISK_ORDER)}


def _compare(op: str, actual: Any, expected: Any, field: str) -> bool:
    if op in ("gte", "lte") and field == "risk_level":
        actual, expected = _RISK_RANK.get(actual, -1), _RISK_RANK.get(expected, -1)
    match op:
        case "eq":
            return actual == expected
        case "ne":
            return actual != expected
        case "gte":
            return actual is not None and actual >= expected
        case "lte":
            return actual is not None and actual <= expected
        case "in":
            return actual in (expected or [])
        case "contains":
            return expected in (actual or [])
        case _:
            logger.warning("Unknown condition op %r — condition fails closed", op)
            return False


def matches(signal: Signal, conditions: list[dict]) -> bool:
    for cond in conditions:
        field = cond.get("field")
        getter = _FIELDS.get(field)
        if getter is None:
            logger.warning("Unknown condition field %r — condition fails closed", field)
            return False
        if not _compare(cond.get("op", "eq"), getter(signal), cond.get("value"), field):
            return False
    return True


# --- Action execution ---------------------------------------------------------

def run_automations(
    db: Session, org: Organization, signal: Signal, engine: IntelligenceEngine
) -> list[ActionRun]:
    runs: list[ActionRun] = []

    # Built-in system rule: high/critical risk always alerts. Not configurable,
    # not deletable — the night-watchman is part of the platform contract.
    if signal.risk_level in (RiskLevel.high, RiskLevel.critical):
        runs.append(_run_alert(db, org, signal, automation=None, config={}))

    automations = (
        db.query(Automation)
        .filter(Automation.organization_id == org.id, Automation.enabled.is_(True))
        .all()
    )
    for automation in automations:
        if not matches(signal, automation.conditions or []):
            continue
        runs.append(_dispatch(db, org, signal, automation, engine))

    db.commit()
    return runs


def _dispatch(
    db: Session,
    org: Organization,
    signal: Signal,
    automation: Automation,
    engine: IntelligenceEngine,
) -> ActionRun:
    handlers = {
        "webhook": _run_webhook,
        "alert": _run_alert,
        "draft_reply": lambda db, org, signal, automation, config: _run_draft_reply(
            db, org, signal, automation, config, engine
        ),
        "tag": _run_tag,
    }
    handler = handlers.get(automation.action_type)
    if handler is None:
        run = ActionRun(
            organization_id=org.id,
            automation_id=automation.id,
            signal_id=signal.id,
            action_type=automation.action_type,
            status="failed",
            detail=f"Unknown action type {automation.action_type!r}",
        )
        db.add(run)
        return run
    try:
        return handler(db, org, signal, automation, automation.action_config or {})
    except Exception as exc:  # an action failure must never poison the pipeline
        logger.exception("Action %s failed for signal %s", automation.action_type, signal.id)
        run = ActionRun(
            organization_id=org.id,
            automation_id=automation.id,
            signal_id=signal.id,
            action_type=automation.action_type,
            status="failed",
            detail=str(exc)[:500],
        )
        db.add(run)
        return run


def _record(
    db: Session,
    org: Organization,
    signal: Signal,
    automation: Automation | None,
    action_type: str,
    status: str,
    detail: str,
) -> ActionRun:
    run = ActionRun(
        organization_id=org.id,
        automation_id=automation.id if automation else None,
        signal_id=signal.id,
        action_type=action_type,
        status=status,
        detail=detail,
    )
    db.add(run)
    return run


def _signal_payload(signal: Signal) -> dict:
    return {
        "id": signal.id,
        "kind": signal.kind.value,
        "content": signal.content,
        "rating": signal.rating,
        "nps_score": signal.nps_score,
        "sentiment": signal.sentiment.value if signal.sentiment else None,
        "sentiment_score": signal.sentiment_score,
        "intent": signal.intent.value if signal.intent else None,
        "urgency": signal.urgency.value if signal.urgency else None,
        "risk_level": signal.risk_level.value,
        "risk_reasons": signal.risk_reasons,
        "churn_risk": signal.churn_risk,
        "topics": signal.topics,
        "summary": signal.summary,
        "occurred_at": signal.occurred_at.isoformat() if signal.occurred_at else None,
    }


def _post(url: str, payload: dict) -> bool:
    try:
        resp = httpx.post(url, json=payload, timeout=5.0)
        return resp.status_code < 400
    except httpx.HTTPError as exc:
        logger.error("Webhook delivery to %s failed: %s", url, exc)
        return False


def _run_webhook(db, org, signal, automation, config) -> ActionRun:
    url = config.get("url", "")
    if not url:
        return _record(db, org, signal, automation, "webhook", "failed", "No url configured")
    ok = _post(url, {"event": "signal.enriched", "signal": _signal_payload(signal)})
    return _record(
        db, org, signal, automation, "webhook", "success" if ok else "failed", f"POST {url}"
    )


def _run_alert(db, org, signal, automation, config) -> ActionRun:
    message = (
        f"[{signal.risk_level.value.upper()}] {org.name}: {signal.summary or signal.content[:140]} "
        f"(reasons: {'; '.join(signal.risk_reasons) or 'rule match'}) — signal #{signal.id}"
    )
    url = config.get("url", "")
    delivered = _post(url, {"text": message, "content": message}) if url else False
    return _record(
        db,
        org,
        signal,
        automation,
        "alert",
        "success",
        message + ("" if delivered or not url else " [webhook delivery failed]"),
    )


def _run_tag(db, org, signal, automation, config) -> ActionRun:
    tags = config.get("tags", [])
    meta = dict(signal.meta or {})
    meta["tags"] = sorted(set(meta.get("tags", [])) | set(tags))
    signal.meta = meta
    return _record(db, org, signal, automation, "tag", "success", f"tags={tags}")


def _run_draft_reply(db, org, signal, automation, config, engine: IntelligenceEngine) -> ActionRun:
    if signal.reply_draft is not None:
        return _record(db, org, signal, automation, "draft_reply", "skipped", "Draft exists")

    voice = db.query(BrandVoice).filter(BrandVoice.organization_id == org.id).first()
    voice_dict = (
        {
            "tone": voice.tone,
            "sign_off": voice.sign_off,
            "language": voice.language,
            "forbidden_phrases": voice.forbidden_phrases,
            "talking_points": voice.talking_points,
            "offer_compensation": voice.offer_compensation,
            "max_words": voice.max_words,
        }
        if voice
        else {}
    )
    from sona.intelligence.schemas import SignalEnrichment

    enrichment = SignalEnrichment(
        sentiment=signal.sentiment or Sentiment.neutral,
        sentiment_score=signal.sentiment_score or 0.0,
        language=signal.language or "en",
        intent=signal.intent or "other",
        urgency=signal.urgency or "low",
        topics=signal.topics or [],
        risk_level=signal.risk_level,
        risk_reasons=signal.risk_reasons or [],
        churn_risk=signal.churn_risk,
        summary=signal.summary or "",
    )
    draft = engine.draft_reply(
        {
            "kind": signal.kind.value,
            "rating": signal.rating,
            "nps_score": signal.nps_score,
            "author_name": (signal.author or {}).get("name", "Anonymous"),
            "content": signal.content,
        },
        enrichment,
        voice_dict,
    )

    # SAFETY GATE — enforced in code, never only in prompts.
    auto_approve = bool(config.get("auto_approve", False))
    safe = (
        signal.risk_level in AUTO_APPROVE_MAX_RISK
        and not draft.escalate_to_human
        and signal.sentiment in (Sentiment.positive, Sentiment.neutral)
    )
    status = ReplyStatus.approved if (auto_approve and safe) else ReplyStatus.pending_approval

    db.add(
        ReplyDraft(
            signal_id=signal.id,
            text=draft.reply_text,
            status=status,
            model=get_settings().sona_model_generate,
        )
    )
    return _record(
        db, org, signal, automation, "draft_reply", "success", f"draft status={status.value}"
    )
