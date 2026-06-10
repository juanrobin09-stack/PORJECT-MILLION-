def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_signup_returns_api_key(org):
    assert org["api_key"].startswith("rsn_")
    assert org["plan"] == "growth"


def test_auth_required(client):
    assert client.get("/v1/locations").status_code == 401
    assert (
        client.get("/v1/locations", headers={"Authorization": "Bearer rsn_bogus"}).status_code
        == 401
    )


def test_brand_voice_upsert(client, auth):
    body = {
        "tone": "playful but never sarcastic",
        "sign_off": "— Sam @ Bluebird",
        "forbidden_phrases": ["we apologize for any inconvenience"],
        "talking_points": ["beans roasted in-house"],
        "offer_compensation": False,
        "max_words": 80,
    }
    resp = client.put("/v1/organizations/me/brand-voice", json=body, headers=auth)
    assert resp.status_code == 200
    assert resp.json()["sign_off"] == "— Sam @ Bluebird"

    # Upsert is idempotent
    resp = client.put("/v1/organizations/me/brand-voice", json=body, headers=auth)
    assert resp.status_code == 200


def test_ingest_review_idempotent(client, auth, location):
    payload = {
        "location_id": location["id"],
        "platform": "google",
        "external_id": "r-1001",
        "author": "Dana M.",
        "rating": 2,
        "text": "Waited 25 minutes for a latte.",
    }
    first = client.post("/v1/reviews/ingest", json=payload, headers=auth)
    assert first.status_code == 202
    second = client.post("/v1/reviews/ingest", json=payload, headers=auth)
    assert second.status_code == 202
    assert second.json()["id"] == first.json()["id"]

    reviews = client.get("/v1/reviews", headers=auth).json()
    assert len(reviews) == 1


def test_cannot_ingest_to_foreign_location(client, auth):
    other = client.post("/v1/organizations", json={"name": "Rival Corp"}).json()
    other_auth = {"Authorization": f"Bearer {other['api_key']}"}
    other_loc = client.post(
        "/v1/locations", json={"name": "Rival HQ"}, headers=other_auth
    ).json()

    resp = client.post(
        "/v1/reviews/ingest",
        json={"location_id": other_loc["id"], "platform": "google", "external_id": "x-1"},
        headers=auth,
    )
    assert resp.status_code == 404


def test_usage_endpoint(client, auth, location):
    usage = client.get("/v1/organizations/me/usage", headers=auth).json()
    assert usage["responses_used"] == 0
    assert usage["responses_quota"] == 600  # growth plan x 1 location
