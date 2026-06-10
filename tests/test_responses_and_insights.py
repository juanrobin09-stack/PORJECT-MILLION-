from app.database import SessionLocal
from app.models import Review
from app.services import insights as insight_service
from app.services import pipeline


def _processed_review(client, auth, location, fake_engine, external_id="r-1"):
    resp = client.post(
        "/v1/reviews/ingest",
        json={
            "location_id": location["id"],
            "platform": "google",
            "external_id": external_id,
            "rating": 2,
            "text": "Slow service.",
        },
        headers=auth,
    )
    db = SessionLocal()
    try:
        review = db.get(Review, resp.json()["id"])
        pipeline.process_review(db, review, engine=fake_engine)
    finally:
        db.close()
    return resp.json()


def test_approval_workflow(client, auth, location, fake_engine):
    _processed_review(client, auth, location, fake_engine)

    pending = client.get("/v1/responses?status=pending_approval", headers=auth).json()
    assert len(pending) == 1
    rid = pending[0]["id"]

    # Edit then approve then publish
    edited = client.patch(f"/v1/responses/{rid}", json={"text": "Custom reply."}, headers=auth)
    assert edited.json()["text"] == "Custom reply."

    approved = client.post(f"/v1/responses/{rid}/approve", headers=auth)
    assert approved.json()["status"] == "approved"

    published = client.post(f"/v1/responses/{rid}/mark-published", headers=auth)
    assert published.json()["status"] == "published"
    assert published.json()["published_at"] is not None

    # Cannot edit after publishing
    assert (
        client.patch(f"/v1/responses/{rid}", json={"text": "x"}, headers=auth).status_code == 409
    )


def test_reject_workflow(client, auth, location, fake_engine):
    _processed_review(client, auth, location, fake_engine)
    rid = client.get("/v1/responses", headers=auth).json()[0]["id"]

    rejected = client.post(f"/v1/responses/{rid}/reject", headers=auth)
    assert rejected.json()["status"] == "rejected"
    # A rejected draft can be re-approved after review
    assert client.post(f"/v1/responses/{rid}/approve", headers=auth).status_code == 200


def test_responses_are_org_scoped(client, auth, location, fake_engine):
    _processed_review(client, auth, location, fake_engine)
    other = client.post("/v1/organizations", json={"name": "Rival"}).json()
    other_auth = {"Authorization": f"Bearer {other['api_key']}"}

    assert client.get("/v1/responses", headers=other_auth).json() == []
    rid = client.get("/v1/responses", headers=auth).json()[0]["id"]
    assert client.post(f"/v1/responses/{rid}/approve", headers=other_auth).status_code == 404


def test_weekly_insights(client, auth, location, fake_engine):
    _processed_review(client, auth, location, fake_engine, external_id="r-a")
    _processed_review(client, auth, location, fake_engine, external_id="r-b")

    db = SessionLocal()
    try:
        from app.models import Organization

        org = db.query(Organization).first()
        report = insight_service.generate_weekly_report(db, org, engine=fake_engine)
        assert report is not None
        assert "Wait times" in report.summary
        assert report.data["top_issues"] == ["wait time"]
    finally:
        db.close()

    listed = client.get("/v1/insights", headers=auth).json()
    assert len(listed) == 1


def test_insights_endpoint_422_when_no_reviews(client, auth):
    resp = client.post("/v1/insights/generate", headers=auth)
    assert resp.status_code == 422
