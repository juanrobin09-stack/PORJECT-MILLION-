import os

os.environ["SONA_DATABASE_URL"] = "sqlite:///./test_sona.db"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient

from sona.database import Base, engine
from sona.intelligence.schemas import DraftedReply, SignalEnrichment, SynthesizedAnswer
from sona.main import app
from sona.models import Intent, RiskLevel, Sentiment, Urgency


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def org(client):
    resp = client.post(
        "/v1/organizations",
        json={"name": "Bluebird Coffee", "industry": "Food & Beverage", "plan": "growth"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def auth(org):
    return {"Authorization": f"Bearer {org['api_key']}"}


@pytest.fixture
def source(client, auth):
    resp = client.post(
        "/v1/sources", json={"name": "Mission St — Google", "kind": "google"}, headers=auth
    )
    assert resp.status_code == 201
    return resp.json()


class FakeIntelligence:
    """Deterministic stand-in for IntelligenceEngine — no network, no key."""

    def __init__(
        self,
        enrichment: SignalEnrichment | None = None,
        draft: DraftedReply | None = None,
        answer: SynthesizedAnswer | None = None,
    ):
        self.enrichment = enrichment or SignalEnrichment(
            sentiment=Sentiment.negative,
            sentiment_score=-0.6,
            language="en",
            intent=Intent.complaint,
            urgency=Urgency.medium,
            topics=["wait-time", "staff-friendliness"],
            risk_level=RiskLevel.low,
            risk_reasons=[],
            churn_risk=False,
            summary="Customer waited 25 minutes and found staff rude.",
        )
        self.draft = draft or DraftedReply(
            reply_text=(
                "Dana, a 25-minute wait is not the bar we hold ourselves to. "
                "We've added a second barista this week. Write me directly: "
                "care@bluebird.coffee — Sam, Manager"
            ),
            addresses_points=["wait time"],
            escalate_to_human=False,
            escalation_reason="",
        )
        self.answer = answer or SynthesizedAnswer(
            answer="Wait time is the dominant complaint: 2 of 2 negative signals mention it.",
            evidence_signal_ids=[1, 2],
            confidence="high",
            caveats="Single channel, small sample.",
        )
        self.enrich_calls = 0
        self.draft_calls = 0

    def enrich(self, signal):
        self.enrich_calls += 1
        return self.enrichment, []

    def draft_reply(self, signal, enrichment, voice):
        self.draft_calls += 1
        return self.draft

    def synthesize(self, question, signal_digest):
        return self.answer


@pytest.fixture
def fake_engine():
    return FakeIntelligence()


def ingest(client, auth, source, external_id="s-1", kind="review", rating=2,
           text="Waited 25 minutes for a latte.", **extra):
    resp = client.post(
        "/v1/signals",
        json={
            "source_id": source["id"],
            "external_id": external_id,
            "kind": kind,
            "rating": rating,
            "content": text,
            "author": {"name": "Dana M."},
            **extra,
        },
        headers=auth,
    )
    assert resp.status_code == 202
    return resp.json()


def process(signal_id, engine):
    from sona import pipeline
    from sona.database import SessionLocal
    from sona.models import Signal

    db = SessionLocal()
    try:
        signal = db.get(Signal, signal_id)
        return pipeline.process_signal(db, signal, engine=engine)
    finally:
        db.close()
