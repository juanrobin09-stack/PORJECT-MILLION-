import os

os.environ["RESONA_DATABASE_URL"] = "sqlite:///./test_resona.db"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.models import RiskLevel, Sentiment
from app.schemas import DraftedResponse, ReviewAnalysis, WeeklyInsights


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
    resp = client.post("/v1/organizations", json={"name": "Bluebird Coffee", "plan": "growth"})
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def auth(org):
    return {"Authorization": f"Bearer {org['api_key']}"}


@pytest.fixture
def location(client, auth):
    resp = client.post(
        "/v1/locations",
        json={"name": "Mission St", "platform_ids": {"google": "loc-1"}},
        headers=auth,
    )
    assert resp.status_code == 201
    return resp.json()


class FakeEngine:
    """Deterministic stand-in for AIEngine — no network, no API key."""

    def __init__(
        self,
        analysis: ReviewAnalysis | None = None,
        draft: DraftedResponse | None = None,
        insights: WeeklyInsights | None = None,
    ):
        self.analysis = analysis or ReviewAnalysis(
            sentiment=Sentiment.negative,
            sentiment_score=-0.6,
            topics=["wait time", "staff friendliness"],
            risk_level=RiskLevel.low,
            risk_reasons=[],
            churn_risk=False,
            summary="Customer waited 25 minutes and found staff rude.",
        )
        self.draft = draft or DraftedResponse(
            response_text=(
                "Dana, a 25-minute wait for a latte is not the bar we hold ourselves to. "
                "We've added a second barista to the morning shift this week. "
                "If you'll give us another shot, write me directly at care@bluebird.coffee. "
                "— Sam, Manager"
            ),
            addresses_complaints=["wait time", "staff attitude"],
            escalate_to_human=False,
            escalation_reason="",
        )
        self.insights = insights or WeeklyInsights(
            executive_summary="Wait times drove 70% of negative sentiment this week.",
            top_strengths=["coffee quality"],
            top_issues=["wait time"],
            emerging_trends=["mobile order pickup confusion"],
            recommended_actions=["add a second register during the 12-2pm rush"],
            locations_at_risk=[],
        )
        self.analyze_calls = 0
        self.draft_calls = 0

    def analyze_review(self, review):
        self.analyze_calls += 1
        return self.analysis

    def draft_response(self, review, analysis, voice):
        self.draft_calls += 1
        return self.draft

    def weekly_insights(self, review_digest, baseline_summary=""):
        return self.insights


@pytest.fixture
def fake_engine():
    return FakeEngine()
