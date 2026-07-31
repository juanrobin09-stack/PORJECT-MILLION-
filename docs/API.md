# Sona — HTTP API Reference

Base URL: `https://api.sona.dev` (local: `http://localhost:8000`)
Interactive docs: `GET /docs`. Auth: `Authorization: Bearer sk_sona_...`
(returned once at signup; only the hash is stored server-side).

---

## Organizations & sources

### `POST /v1/organizations` — sign up
```json
{ "name": "Bluebird Coffee", "industry": "food & beverage", "plan": "growth" }
```
Plans: `developer` (free, 500 signals/mo) · `growth` ($499, 10k) · `scale`
($1,990, 100k) · `enterprise` (custom, unlimited). `industry` drives benchmark
segmentation. Response includes `api_key` — shown once.

### `GET /v1/organizations/me` · `GET /v1/organizations/me/usage`
```json
{ "plan": "growth", "period": "current_month", "signals_enriched": 4120, "signal_quota": 10000 }
```

### `POST /v1/sources` / `GET /v1/sources`
```json
{ "name": "Google — Mission St", "kind": "google",
  "config": { "location_name": "accounts/1/locations/42" } }
```
`kind`: `api` (push via the ingest endpoint) or a connector kind
(`google`, `trustpilot`) polled by the worker.

---

## Signals

### `POST /v1/signals` — ingest anything (202)
```json
{
  "source_id": 1, "external_id": "r-1001", "kind": "review",
  "author": { "name": "Dana M.", "customer_id": "c_812" },
  "content": "Waited 25 minutes for a latte.", "rating": 2,
  "meta": { "store": "mission-st" }
}
```
`kind`: `review` | `nps` | `support_ticket` | `chat` | `survey` | `social` |
`custom`. `nps_score` (0-10) for NPS. Idempotent on
`(source_id, external_id)`. Enrichment + automations run async after the 202.

### `GET /v1/signals` — query the canonical store
Filters: `source_id`, `kind`, `sentiment`, `intent`, `risk_level`, `topic`
(canonical slug), `churn_risk`, `limit` (≤200), `offset`.

Enriched signal:
```json
{
  "id": 17, "kind": "review", "rating": 2, "content": "...",
  "sentiment": "negative", "sentiment_score": -0.62, "language": "en",
  "intent": "complaint", "urgency": "medium",
  "risk_level": "low", "risk_reasons": [], "churn_risk": false,
  "topics": ["wait-time", "staff-friendliness"], "raw_topics": [],
  "summary": "Customer waited 25 minutes and found staff rude.",
  "enriched_at": "2026-06-10T09:14:02Z"
}
```

### `GET /v1/signals/{id}`

---

## Ask — natural-language answers

### `POST /v1/ask`
```json
{ "question": "What do detractors mention that promoters don't?",
  "kind": "nps", "days": 30, "max_signals": 200 }
```
```json
{
  "answer": "Billing confusion: 9 of 31 detractor verbatims mention unexpected charges; no promoter does.",
  "evidence_signal_ids": [203, 211, 217],
  "confidence": "high",
  "caveats": "NPS channel only; 30-day window.",
  "signals_considered": 184
}
```
Evidence IDs are validated server-side against the tenant's own signals.
`422` when no enriched signals match the window.

---

## Automations

### `POST /v1/automations`
```json
{
  "name": "Page on-call for churning detractors",
  "conditions": [
    { "field": "churn_risk", "op": "eq", "value": true },
    { "field": "sentiment_score", "op": "lte", "value": -0.5 }
  ],
  "action_type": "webhook",
  "action_config": { "url": "https://hooks.slack.com/services/..." }
}
```
Condition fields: `kind`, `sentiment`, `sentiment_score`, `intent`, `urgency`,
`risk_level` (ordered `gte`/`lte`), `churn_risk`, `rating`, `nps_score`,
`topics` (`contains`), `language`. Ops: `eq ne gte lte in contains`.
AND-combined; invalid fields/ops are rejected with `422`.

Actions:
| `action_type` | `action_config` | Effect |
|---|---|---|
| `webhook` | `{"url": ...}` | POST the enriched signal to your stack |
| `alert` | `{"url": ...}` (optional) | Persist alert + optional webhook |
| `draft_reply` | `{"auto_approve": bool}` | AI reply via the reputation module. Auto-approve is code-gated: risky/escalated/negative signals always require a human. |
| `tag` | `{"tags": [...]}` | Append tags to signal metadata |

Built-in, non-configurable: risk `high`/`critical` always raises an alert.

### `GET /v1/automations` · `DELETE /v1/automations/{id}`
### `GET /v1/action-runs?signal_id=&action_type=` — the audit log

---

## Benchmarks

### `GET /v1/benchmarks?period=2026-06`
Anonymized topic aggregates for your industry, published only when at least
`SONA_BENCHMARK_MIN_ORGS` distinct organizations contribute (k-anonymity):
```json
[{ "industry": "food & beverage", "topic": "wait-time", "period": "2026-06",
   "org_count": 31, "signal_count": 1842,
   "avg_sentiment": -0.41, "negative_share": 0.63 }]
```

---

## Reputation module

| Endpoint | Effect |
|---|---|
| `PUT /v1/reputation/brand-voice` | Voice profile: tone, sign-off, language, forbidden phrases, talking points, compensation policy, word limit |
| `GET /v1/reputation/drafts?status=pending_approval` | Approval inbox |
| `PATCH /v1/reputation/drafts/{id}` | Edit (resets to pending) |
| `POST /v1/reputation/drafts/{id}/approve` · `/reject` · `/mark-published` | Workflow: pending → approved → published; rejected is re-approvable |

---

## Errors

`401` bad/missing key · `404` not found or not yours (existence never leaks) ·
`409` invalid state transition · `422` validation / empty window · `503` AI
not configured on this deployment.
