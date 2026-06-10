# Resona — HTTP API Reference

Base URL: `https://api.resona.app` (local: `http://localhost:8000`)
Interactive docs: `GET /docs` (OpenAPI/Swagger, auto-generated).

## Authentication

Every endpoint except signup and `/health` requires the org API key:

```
Authorization: Bearer rsn_...
```

The key is returned once at signup. Treat it like a password.

---

## Organizations

### `POST /v1/organizations` — sign up
```json
{ "name": "Bluebird Coffee", "plan": "growth" }
```
Plans: `starter` | `growth` | `scale`. Returns the org including `api_key`.

### `GET /v1/organizations/me` — current org

### `GET /v1/organizations/me/usage` — quota status
```json
{ "plan": "growth", "period": "current_month", "responses_used": 412, "responses_quota": 600 }
```
`responses_quota` is `null` on the Scale plan (unlimited). Quota = per-plan
allowance × active locations, resets on the 1st (UTC).

### `PUT /v1/organizations/me/brand-voice` — voice profile
The contract that governs every AI reply:
```json
{
  "tone": "playful but never sarcastic; we're neighbors, not a corporation",
  "sign_off": "— Sam @ Bluebird",
  "language": "auto",
  "forbidden_phrases": ["we apologize for any inconvenience"],
  "talking_points": ["beans roasted in-house daily"],
  "offer_compensation": false,
  "max_words": 80
}
```
`language: "auto"` mirrors the reviewer's language. `offer_compensation: false`
hard-forbids the AI from mentioning refunds/discounts/freebies.

---

## Locations

### `POST /v1/locations`
```json
{
  "name": "Bluebird — Mission St",
  "platform_ids": { "google": "accounts/1/locations/42", "trustpilot": "5f1..." },
  "response_mode": "approve"
}
```
`response_mode`: `draft_only` | `approve` (default) | `auto_publish`.
Under `auto_publish`, only positive/neutral reviews with risk ≤ low and no AI
escalation flag are auto-approved; everything else still requires a human.

### `GET /v1/locations`

---

## Reviews

### `POST /v1/reviews/ingest` — webhook ingestion (202)
```json
{
  "location_id": 1,
  "platform": "google",
  "external_id": "r-1001",
  "author": "Dana M.",
  "rating": 2,
  "text": "Waited 25 minutes for a latte and the barista was rude about it."
}
```
Idempotent on `(platform, external_id)` — re-deliveries return the existing
review. Analysis and drafting run asynchronously after the 202.

### `GET /v1/reviews` — list with filters
Query params: `location_id`, `sentiment` (`positive|neutral|negative|mixed`),
`risk_level` (`none|low|medium|high|critical`), `limit` (≤200), `offset`.

Each review carries its AI analysis once processed:
```json
{
  "id": 17, "rating": 2, "text": "...",
  "sentiment": "negative", "sentiment_score": -0.62,
  "topics": ["wait time", "staff friendliness"],
  "risk_level": "low", "risk_reasons": [], "churn_risk": false,
  "analyzed_at": "2026-06-10T09:14:02Z"
}
```

### `GET /v1/reviews/{id}`

---

## Responses (drafts → published)

Status machine: `pending_approval → approved → published`, with `rejected`
re-approvable after edits.

| Endpoint | Effect |
|---|---|
| `GET /v1/responses?status=pending_approval` | The approval inbox |
| `PATCH /v1/responses/{id}` `{"text": "..."}` | Edit draft (resets to pending) |
| `POST /v1/responses/{id}/approve` | Approve for publishing |
| `POST /v1/responses/{id}/reject` | Reject |
| `POST /v1/responses/{id}/mark-published` | Record publication (publisher worker or manual) |

---

## Insights & alerts

| Endpoint | Effect |
|---|---|
| `GET /v1/insights` | Past weekly reports (newest first) |
| `POST /v1/insights/generate` | Generate trailing-7-day report now (422 if no analyzed reviews) |
| `GET /v1/alerts` | Risk alerts (high/critical reviews) |

Weekly report payload (`data`):
```json
{
  "executive_summary": "Wait times drove 70% of negative sentiment this week...",
  "top_strengths": ["coffee quality", "baristas remember regulars"],
  "top_issues": ["wait time", "mobile order pickup confusion"],
  "emerging_trends": ["oat milk stockouts mentioned 4x, first time"],
  "recommended_actions": ["add a second register during the 12-2pm rush"],
  "locations_at_risk": ["Mission St"]
}
```

---

## Errors

Standard HTTP semantics: `401` bad/missing key · `404` not found or not yours
(tenant isolation never reveals existence) · `409` invalid state transition ·
`422` validation / nothing to report · `429` reserved for rate limiting.
