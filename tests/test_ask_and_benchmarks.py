import pytest

from sona import benchmarks
from sona.api import ask as ask_module
from sona.database import SessionLocal
from sona.intelligence import engine as engine_module
from tests.conftest import FakeIntelligence, ingest, process


def test_ask_synthesizes_over_own_signals(client, auth, source, fake_engine, monkeypatch):
    a = ingest(client, auth, source, external_id="s-a")
    b = ingest(client, auth, source, external_id="s-b", text="Line was endless again.")
    process(a["id"], fake_engine)
    process(b["id"], fake_engine)

    monkeypatch.setattr(ask_module.get_settings(), "anthropic_api_key", "test-key")
    monkeypatch.setattr(engine_module, "_engine", fake_engine)

    resp = client.post(
        "/v1/ask", json={"question": "What do customers complain about most?"}, headers=auth
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "Wait time" in body["answer"]
    assert body["signals_considered"] == 2
    assert set(body["evidence_signal_ids"]) <= {a["id"], b["id"]}  # foreign IDs filtered


def test_ask_422_when_no_enriched_signals(client, auth, monkeypatch):
    monkeypatch.setattr(ask_module.get_settings(), "anthropic_api_key", "test-key")
    resp = client.post("/v1/ask", json={"question": "Anything?"}, headers=auth)
    assert resp.status_code == 422


def _org_with_signals(client, fake_engine, name, industry="food & beverage"):
    org = client.post("/v1/organizations", json={"name": name, "industry": industry}).json()
    auth = {"Authorization": f"Bearer {org['api_key']}"}
    source = client.post("/v1/sources", json={"name": "main", "kind": "api"}, headers=auth).json()
    s = ingest(client, auth, source, external_id=f"{name}-1")
    process(s["id"], fake_engine)
    return auth


@pytest.fixture
def two_org_benchmark_db(client, fake_engine):
    auth_a = _org_with_signals(client, fake_engine, "Org A")
    auth_b = _org_with_signals(client, fake_engine, "Org B")
    db = SessionLocal()
    try:
        benchmarks.compute_benchmarks(db)
    finally:
        db.close()
    return auth_a, auth_b


def test_benchmarks_aggregate_across_tenants(two_org_benchmark_db):
    db = SessionLocal()
    try:
        stats = benchmarks.published_benchmarks(db, "food & beverage", min_orgs=2)
        by_topic = {s.topic: s for s in stats}
        assert by_topic["wait-time"].org_count == 2
        assert by_topic["wait-time"].signal_count == 2
        assert by_topic["wait-time"].negative_share == 1.0
        assert by_topic["wait-time"].avg_sentiment == pytest.approx(-0.6)
    finally:
        db.close()


def test_k_anonymity_hides_thin_segments(two_org_benchmark_db):
    db = SessionLocal()
    try:
        # Threshold above contributor count -> nothing published
        assert benchmarks.published_benchmarks(db, "food & beverage", min_orgs=3) == []
        # Unknown industry -> nothing
        assert benchmarks.published_benchmarks(db, "aerospace", min_orgs=1) == []
    finally:
        db.close()


def test_benchmark_endpoint_respects_default_threshold(two_org_benchmark_db, client):
    auth_a, _ = two_org_benchmark_db
    # Default SONA_BENCHMARK_MIN_ORGS=5 > 2 contributors -> empty by design
    assert client.get("/v1/benchmarks", headers=auth_a).json() == []
