from sona.database import SessionLocal
from sona.intelligence.schemas import DraftedReply, SignalEnrichment
from sona.models import Intent, RiskLevel, Sentiment, Signal, Urgency
from tests.conftest import FakeIntelligence, ingest, process


def _draft_reply_automation(client, auth, auto_approve=False):
    resp = client.post(
        "/v1/automations",
        json={
            "name": "Reply to reviews",
            "conditions": [{"field": "kind", "op": "eq", "value": "review"}],
            "action_type": "draft_reply",
            "action_config": {"auto_approve": auto_approve},
        },
        headers=auth,
    )
    assert resp.status_code == 201
    return resp.json()


def test_condition_validation(client, auth):
    bad_field = client.post(
        "/v1/automations",
        json={
            "name": "x",
            "conditions": [{"field": "nonsense", "op": "eq", "value": 1}],
            "action_type": "tag",
        },
        headers=auth,
    )
    assert bad_field.status_code == 422
    bad_action = client.post(
        "/v1/automations",
        json={"name": "x", "conditions": [], "action_type": "rm_rf"},
        headers=auth,
    )
    assert bad_action.status_code == 422


def test_draft_reply_automation_creates_pending_draft(client, auth, source, fake_engine):
    _draft_reply_automation(client, auth)
    ingested = ingest(client, auth, source)
    process(ingested["id"], fake_engine)

    drafts = client.get("/v1/reputation/drafts?status=pending_approval", headers=auth).json()
    assert len(drafts) == 1
    assert "Dana" in drafts[0]["text"]
    assert fake_engine.draft_calls == 1


def test_safety_gate_blocks_auto_approve_for_risky_signals(client, auth, source):
    """auto_approve=True must be overridden in code for risky/escalated signals."""
    _draft_reply_automation(client, auth, auto_approve=True)
    engine = FakeIntelligence(
        enrichment=SignalEnrichment(
            sentiment=Sentiment.negative,
            sentiment_score=-0.9,
            language="en",
            intent=Intent.legal_threat,
            urgency=Urgency.critical,
            topics=["trust-integrity"],
            risk_level=RiskLevel.high,
            risk_reasons=["threat of legal action"],
            churn_risk=True,
            summary="Customer threatens to sue.",
        ),
        draft=DraftedReply(reply_text="We hear you.", escalate_to_human=True,
                           escalation_reason="legal threat"),
    )
    ingested = ingest(client, auth, source, external_id="r-legal", rating=1,
                      text="My lawyer will hear about this.")
    process(ingested["id"], engine)

    drafts = client.get("/v1/reputation/drafts", headers=auth).json()
    assert drafts[0]["status"] == "pending_approval"  # never auto-approved


def test_auto_approve_for_safe_positive_signals(client, auth, source):
    _draft_reply_automation(client, auth, auto_approve=True)
    engine = FakeIntelligence(
        enrichment=SignalEnrichment(
            sentiment=Sentiment.positive,
            sentiment_score=0.9,
            language="en",
            intent=Intent.praise,
            urgency=Urgency.low,
            topics=["food-quality"],
            risk_level=RiskLevel.none,
            risk_reasons=[],
            churn_risk=False,
            summary="Customer loved the cortado.",
        ),
        draft=DraftedReply(reply_text="So glad the cortado hit the spot!",
                           escalate_to_human=False),
    )
    ingested = ingest(client, auth, source, external_id="r-pos", rating=5, text="Best cortado!")
    process(ingested["id"], engine)

    drafts = client.get("/v1/reputation/drafts", headers=auth).json()
    assert drafts[0]["status"] == "approved"


def test_tag_action_and_topic_condition(client, auth, source, fake_engine):
    client.post(
        "/v1/automations",
        json={
            "name": "Tag wait-time complaints",
            "conditions": [
                {"field": "topics", "op": "contains", "value": "wait-time"},
                {"field": "sentiment", "op": "eq", "value": "negative"},
            ],
            "action_type": "tag",
            "action_config": {"tags": ["ops-review"]},
        },
        headers=auth,
    )
    ingested = ingest(client, auth, source)
    process(ingested["id"], fake_engine)

    db = SessionLocal()
    try:
        signal = db.get(Signal, ingested["id"])
        assert signal.meta.get("tags") == ["ops-review"]
    finally:
        db.close()


def test_non_matching_automation_does_not_fire(client, auth, source, fake_engine):
    client.post(
        "/v1/automations",
        json={
            "name": "NPS detractors only",
            "conditions": [{"field": "kind", "op": "eq", "value": "nps"}],
            "action_type": "tag",
            "action_config": {"tags": ["detractor"]},
        },
        headers=auth,
    )
    ingested = ingest(client, auth, source)  # kind=review
    process(ingested["id"], fake_engine)
    assert client.get("/v1/action-runs?action_type=tag", headers=auth).json() == []


def test_reply_approval_workflow(client, auth, source, fake_engine):
    _draft_reply_automation(client, auth)
    ingested = ingest(client, auth, source)
    process(ingested["id"], fake_engine)

    draft_id = client.get("/v1/reputation/drafts", headers=auth).json()[0]["id"]

    edited = client.patch(
        f"/v1/reputation/drafts/{draft_id}", json={"text": "Custom reply."}, headers=auth
    )
    assert edited.json()["text"] == "Custom reply."

    assert (
        client.post(f"/v1/reputation/drafts/{draft_id}/approve", headers=auth).json()["status"]
        == "approved"
    )
    published = client.post(
        f"/v1/reputation/drafts/{draft_id}/mark-published", headers=auth
    ).json()
    assert published["status"] == "published"
    assert (
        client.patch(
            f"/v1/reputation/drafts/{draft_id}", json={"text": "x"}, headers=auth
        ).status_code
        == 409
    )
