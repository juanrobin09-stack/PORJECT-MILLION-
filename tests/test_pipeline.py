from app.database import SessionLocal
from app.models import (
    Organization,
    ResponseMode,
    ResponseStatus,
    Review,
    RiskLevel,
    Sentiment,
)
from app.schemas import DraftedResponse, ReviewAnalysis
from app.services import pipeline
from tests.conftest import FakeEngine


def _ingest(client, auth, location, external_id="r-1", rating=2, text="Slow service."):
    resp = client.post(
        "/v1/reviews/ingest",
        json={
            "location_id": location["id"],
            "platform": "google",
            "external_id": external_id,
            "rating": rating,
            "text": text,
        },
        headers=auth,
    )
    assert resp.status_code == 202
    return resp.json()


def test_pipeline_analyzes_and_drafts(client, auth, location, fake_engine):
    ingested = _ingest(client, auth, location)
    db = SessionLocal()
    try:
        review = db.get(Review, ingested["id"])
        pipeline.process_review(db, review, engine=fake_engine)

        assert review.sentiment == Sentiment.negative
        assert review.topics == ["wait time", "staff friendliness"]
        assert review.analyzed_at is not None
        assert fake_engine.analyze_calls == 1
        assert fake_engine.draft_calls == 1
        assert review.response is not None
        assert review.response.status == ResponseStatus.pending_approval
        assert "Dana" in review.response.text
    finally:
        db.close()


def test_high_risk_raises_alert_and_never_autopublishes(client, auth, location):
    engine = FakeEngine(
        analysis=ReviewAnalysis(
            sentiment=Sentiment.negative,
            sentiment_score=-0.9,
            topics=["food safety"],
            risk_level=RiskLevel.high,
            risk_reasons=["health/safety claim: food poisoning allegation"],
            churn_risk=True,
            summary="Customer alleges food poisoning.",
        ),
        draft=DraftedResponse(
            response_text="We take this seriously...",
            escalate_to_human=True,
            escalation_reason="health claim",
        ),
    )
    # Switch location to auto_publish to prove the safety override wins
    db = SessionLocal()
    try:
        from app.models import Location

        loc = db.get(Location, location["id"])
        loc.response_mode = ResponseMode.auto_publish
        db.commit()

        ingested = _ingest(client, auth, location, external_id="r-risk", rating=1)
        review = db.get(Review, ingested["id"])
        pipeline.process_review(db, review, engine=engine)

        assert review.risk_level == RiskLevel.high
        assert review.response.status == ResponseStatus.pending_approval  # NOT auto-approved
    finally:
        db.close()

    alerts = client.get("/v1/alerts", headers=auth).json()
    assert len(alerts) == 1
    assert alerts[0]["level"] == "high"
    assert "food poisoning" in alerts[0]["message"]


def test_auto_publish_routes_safe_positive_reviews(client, auth, location):
    engine = FakeEngine(
        analysis=ReviewAnalysis(
            sentiment=Sentiment.positive,
            sentiment_score=0.9,
            topics=["coffee quality"],
            risk_level=RiskLevel.none,
            risk_reasons=[],
            churn_risk=False,
            summary="Customer loved the coffee.",
        ),
        draft=DraftedResponse(
            response_text="So glad the cortado hit the spot!",
            escalate_to_human=False,
        ),
    )
    db = SessionLocal()
    try:
        from app.models import Location

        loc = db.get(Location, location["id"])
        loc.response_mode = ResponseMode.auto_publish
        db.commit()

        ingested = _ingest(client, auth, location, external_id="r-pos", rating=5, text="Best cortado!")
        review = db.get(Review, ingested["id"])
        pipeline.process_review(db, review, engine=engine)
        assert review.response.status == ResponseStatus.approved
    finally:
        db.close()


def test_quota_blocks_drafting_but_not_analysis(client, auth, location, fake_engine):
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        from app.models import UsageRecord

        # Exhaust the growth quota (600 x 1 location)
        for _ in range(600):
            db.add(UsageRecord(organization_id=org.id))
        db.commit()

        ingested = _ingest(client, auth, location, external_id="r-quota")
        review = db.get(Review, ingested["id"])
        pipeline.process_review(db, review, engine=fake_engine)

        assert review.analyzed_at is not None      # analysis always runs
        assert review.response is None             # drafting blocked
        assert fake_engine.draft_calls == 0
    finally:
        db.close()
