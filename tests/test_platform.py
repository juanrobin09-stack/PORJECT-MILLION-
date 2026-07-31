from sona.database import SessionLocal
from sona.models import Organization
from tests.conftest import ingest


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["version"].startswith("2.")


def test_signup_returns_key_once_and_stores_only_hash(client, org):
    assert org["api_key"].startswith("sk_sona_")
    assert org["industry"] == "food & beverage"

    db = SessionLocal()
    try:
        row = db.get(Organization, org["id"])
        assert org["api_key"] not in (row.api_key_hash or "")
        assert len(row.api_key_hash) == 64  # sha256 hex
    finally:
        db.close()

    # /me does not leak the key
    me = client.get(
        "/v1/organizations/me", headers={"Authorization": f"Bearer {org['api_key']}"}
    ).json()
    assert "api_key" not in me


def test_auth_required_and_invalid_key_rejected(client):
    assert client.get("/v1/sources").status_code == 401
    assert (
        client.get("/v1/sources", headers={"Authorization": "Bearer sk_sona_bogus"}).status_code
        == 401
    )


def test_signal_ingest_idempotent(client, auth, source):
    first = ingest(client, auth, source, external_id="r-1001")
    second = ingest(client, auth, source, external_id="r-1001")
    assert second["id"] == first["id"]
    assert len(client.get("/v1/signals", headers=auth).json()) == 1


def test_cross_tenant_isolation(client, auth, source):
    ingest(client, auth, source, external_id="r-1")

    other = client.post(
        "/v1/organizations", json={"name": "Rival", "industry": "food & beverage"}
    ).json()
    other_auth = {"Authorization": f"Bearer {other['api_key']}"}

    assert client.get("/v1/signals", headers=other_auth).json() == []
    # Foreign source rejected on ingest
    resp = client.post(
        "/v1/signals",
        json={"source_id": source["id"], "external_id": "x-1"},
        headers=other_auth,
    )
    assert resp.status_code == 404
    # Foreign signal invisible by id
    sid = client.get("/v1/signals", headers=auth).json()[0]["id"]
    assert client.get(f"/v1/signals/{sid}", headers=other_auth).status_code == 404


def test_multi_kind_ingestion(client, auth, source):
    ingest(client, auth, source, external_id="n-1", kind="nps", rating=None, nps_score=3,
           text="Too expensive for what it is.")
    ingest(client, auth, source, external_id="t-1", kind="support_ticket", rating=None,
           text="My order arrived broken.")
    kinds = {s["kind"] for s in client.get("/v1/signals", headers=auth).json()}
    assert kinds == {"nps", "support_ticket"}


def test_usage_endpoint(client, auth):
    usage = client.get("/v1/organizations/me/usage", headers=auth).json()
    assert usage == {
        "plan": "growth",
        "period": "current_month",
        "signals_enriched": 0,
        "signal_quota": 10000,
    }
