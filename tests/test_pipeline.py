from sona.database import SessionLocal
from sona.intelligence.schemas import SignalEnrichment
from sona.models import Intent, Organization, RiskLevel, Sentiment, Signal, Urgency, UsageRecord
from tests.conftest import FakeIntelligence, ingest, process


def test_enrichment_populates_canonical_fields(client, auth, source, fake_engine):
    ingested = ingest(client, auth, source)
    process(ingested["id"], fake_engine)

    signal = client.get(f"/v1/signals/{ingested['id']}", headers=auth).json()
    assert signal["sentiment"] == "negative"
    assert signal["intent"] == "complaint"
    assert signal["topics"] == ["wait-time", "staff-friendliness"]
    assert signal["language"] == "en"
    assert signal["enriched_at"] is not None
    assert fake_engine.enrich_calls == 1

    # Enrichment is metered
    usage = client.get("/v1/organizations/me/usage", headers=auth).json()
    assert usage["signals_enriched"] == 1


def test_pipeline_idempotent(client, auth, source, fake_engine):
    ingested = ingest(client, auth, source)
    process(ingested["id"], fake_engine)
    process(ingested["id"], fake_engine)
    assert fake_engine.enrich_calls == 1


def test_taxonomy_normalization_in_engine():
    """Free-form labels are normalized in code, not just by the prompt."""
    from sona.core.taxonomy import normalize_topics

    canonical, unmapped = normalize_topics(
        ["wait time", "Slow service", "wait-time", "quantum entanglement"]
    )
    assert canonical == ["wait-time"]
    assert unmapped == ["quantum entanglement"]


def test_high_risk_always_alerts_via_system_rule(client, auth, source):
    engine = FakeIntelligence(
        enrichment=SignalEnrichment(
            sentiment=Sentiment.negative,
            sentiment_score=-0.9,
            language="en",
            intent=Intent.safety_issue,
            urgency=Urgency.critical,
            topics=["safety"],
            risk_level=RiskLevel.high,
            risk_reasons=["health/safety claim: food poisoning allegation"],
            churn_risk=True,
            summary="Customer alleges food poisoning.",
        )
    )
    ingested = ingest(client, auth, source, external_id="r-risk", rating=1,
                      text="I got food poisoning here.")
    process(ingested["id"], engine)

    runs = client.get("/v1/action-runs?action_type=alert", headers=auth).json()
    assert len(runs) == 1
    assert runs[0]["automation_id"] is None  # built-in system rule
    assert "food poisoning" in runs[0]["detail"]


def test_quota_blocks_enrichment_but_stores_signal(client, auth, source, fake_engine):
    db = SessionLocal()
    try:
        org_row = db.query(Organization).first()
        for _ in range(10_000):  # exhaust growth quota
            db.add(UsageRecord(organization_id=org_row.id))
        db.commit()
    finally:
        db.close()

    ingested = ingest(client, auth, source, external_id="r-quota")
    process(ingested["id"], fake_engine)

    assert fake_engine.enrich_calls == 0
    db = SessionLocal()
    try:
        signal = db.get(Signal, ingested["id"])
        assert signal is not None and signal.enriched_at is None  # stored raw, never dropped
    finally:
        db.close()
