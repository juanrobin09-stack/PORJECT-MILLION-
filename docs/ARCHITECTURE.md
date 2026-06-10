# Resona — Architecture

## System overview

```
                         ┌──────────────────────────────────────────────┐
  Google Business ──┐    │                   RESONA                     │
  Trustpilot ───────┼──▶ │  worker.py (poller)        FastAPI (app/)    │ ◀── Dashboard / API clients
  Any source ───────┘    │        │                        │            │
   (webhook)             │        ▼                        ▼            │
                         │  ┌─────────────────────────────────────┐     │
                         │  │        PIPELINE (services/)         │     │
                         │  │ ingest → analyze → alert → quota →  │     │
                         │  │ draft → route (approve/auto/draft)  │     │
                         │  └──────┬───────────────┬──────────────┘     │
                         │         │               │                    │
                         │     Claude API      PostgreSQL               │
                         │  (Haiku triage,    (SQLite in dev)           │
                         │   Opus writing/                              │
                         │   insights)                                  │
                         └──────────────────────────────────────────────┘
```

Two processes share one database:

| Process | Entry point | Responsibility |
|---|---|---|
| API | `uvicorn app.main:app` | HTTP surface: signup, locations, ingest webhook, approval workflow, insights, alerts |
| Worker | `python -m app.worker` | Polls connectors every 15 min; generates weekly insight reports |

Both are stateless; horizontal scaling is adding replicas behind a load balancer
(worker scaling requires partitioning locations or moving to a queue — see
Scaling path below).

## The pipeline (`app/services/pipeline.py`)

Every review, regardless of source, flows through `process_review`:

1. **Analyze** — Claude Haiku 4.5 returns a `ReviewAnalysis` (sentiment, score,
   topics, risk level, churn flag) via structured outputs. Star rating is
   treated as a hint only; the text wins.
2. **Alert** — `high`/`critical` risk raises a persisted `Alert` and fires the
   configured Slack/Discord webhook *before* anything else happens. Owners hear
   about a food-poisoning claim from Resona, not from a journalist.
3. **Quota** — analysis is always free; the AI-drafted response is the billable
   unit, checked against the plan quota (`usage.py`).
4. **Draft** — Claude Opus 4.8 writes the reply, governed by the org's
   `BrandVoice` profile, and returns a `DraftedResponse` including its own
   `escalate_to_human` judgment.
5. **Route** — three response modes per location:
   - `draft_only`: drafts pile up for export; customer publishes manually.
   - `approve` (default): drafts enter `pending_approval`; a human approves.
   - `auto_publish`: positive/neutral + risk ≤ low + no escalation flag →
     auto-approved for the publisher. Anything delicate falls back to approval.
     **The safety override is non-negotiable code, not a prompt suggestion.**

## AI layer design (`app/ai/`)

| Concern | Decision | Why |
|---|---|---|
| Output integrity | `client.messages.parse()` + Pydantic schemas everywhere | No JSON-repair paths; malformed output is impossible by contract |
| Cost | Static system prompts with `cache_control: ephemeral` | Per-review marginal tokens = the review text itself (~100-300 tokens) |
| Model tiers | Haiku 4.5 (analysis) / Opus 4.8 (writing, insights) | Volume work goes to the cheap model; the *product* — writing quality and judgment — gets the best model |
| Insights | Opus 4.8 with adaptive thinking over a pre-aggregated digest | The service compacts a week of reviews into a counted digest first, controlling token spend and grounding claims in counts |
| Testability | `AIEngine` takes an injectable client; tests use `FakeEngine` | The full suite runs with no network and no API key |

### Inference unit economics

A typical review: ~1,300 cached system tokens (≈free after first hit), ~200
input tokens, ~150 output tokens.

| Step | Model | Cost/review (approx) |
|---|---|---|
| Analysis | Haiku 4.5 ($1/$5 per MTok) | ~$0.001 |
| Response | Opus 4.8 ($5/$25 per MTok) | ~$0.006 |
| **Total** | | **< $0.01** |

At Growth-plan pricing ($99 for 600 responses), inference is < 5% of revenue.

## Data model

```
Organization 1─1 BrandVoice
Organization 1─* Location 1─* Review 1─1 ReviewResponse
Organization 1─* Alert, InsightReport, UsageRecord
```

- `Review` is idempotent on `(platform, external_id)` — connectors and webhooks
  can re-deliver safely.
- `UsageRecord` is append-only: one row per billable draft, summed per calendar
  month for quota and exported to Stripe metered billing.
- All AI analysis is stored *on* the review row (denormalized) because it is
  written once and read constantly by filters and the insight digest.

## Security model

- Auth: per-org bearer API keys (`rsn_` + 256-bit token), hashed-at-rest is the
  first hardening step before public launch (see ROADMAP).
- Tenant isolation enforced in every query via `organization_id` joins; tests
  assert cross-tenant 404s.
- The Anthropic key lives server-side only; customers never touch model config.
- Review text is untrusted input: it is only ever placed in the user turn of a
  prompt, never in system prompts, and responses pass through the structured-
  output contract plus the escalation gate before any auto-publish.

## Scaling path

| Stage | Bottleneck | Move |
|---|---|---|
| 0 → 1k locations | none | current architecture (Postgres + 2 containers) |
| 1k → 10k | polling fan-out | swap APScheduler for a queue (e.g. Redis + workers), partition locations |
| 10k+ | inference throughput | Anthropic Batches API for non-urgent analysis (50% cost), keep drafts real-time |
| Always | cost | prompt-cache hit rate monitoring via `usage.cache_read_input_tokens` |
