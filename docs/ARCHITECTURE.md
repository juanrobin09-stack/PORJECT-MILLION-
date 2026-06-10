# Sona — Architecture

## System overview

```
 reviews / NPS / tickets / chats / surveys / social
        │                          │
   connectors (worker)        POST /v1/signals
        └────────────┬─────────────┘
                     ▼
        ┌─────────────────────────────┐
        │   PIPELINE (pipeline.py)    │
        │ ingest → enrich → automate  │
        │        → meter              │
        └───────┬───────────┬─────────┘
                │           │
           Claude API   PostgreSQL ──▶ nightly benchmark job
        (Haiku enrich,               (cross-tenant k-anonymous
         Opus generate)               aggregates)
                     ▲
        FastAPI: signals · ask · automations · benchmarks · reputation
```

Two stateless processes share one database:

| Process | Entry point | Responsibility |
|---|---|---|
| API | `uvicorn sona.main:app` | Ingest, query, ask, automations CRUD, approval workflow, benchmarks |
| Worker | `python -m sona.worker` | Connector polling (15 min), nightly benchmark recompute |

## The canonical schema — the strategic core

`Signal` is one table for every kind of feedback. Channel differences are
absorbed at the edge (connectors / the ingest endpoint); everything inside the
platform — enrichment, automations, ask, benchmarks, modules — operates on the
canonical shape only. Consequences:

- Adding a channel = implementing one connector interface. Nothing else moves.
- One automation rule spans every channel ("negative + churn_risk" matches a
  review and an NPS verbatim identically).
- Cross-tenant aggregation is possible at all (see Benchmarks).

The **taxonomy** (`sona/core/taxonomy.py`) is the schema's vocabulary: ~40
versioned canonical topic slugs + a synonym map. The model is instructed to use
slugs, and `normalize_topics()` enforces it in code; unmapped labels are kept
as `raw_topics` — the harvest queue for taxonomy growth. Taxonomy discipline
is what makes "wait-time" comparable across a coffee chain and a dental group.

## Pipeline (`sona/pipeline.py`)

1. **Ingest** — idempotent on `(source_id, external_id)`; signals are never
   dropped (over-quota signals are stored raw and enriched retroactively on
   upgrade — the upgrade path is visible in the product).
2. **Enrich** — one structured-output call (`messages.parse` against
   `SignalEnrichment`): sentiment ±score, language, intent, urgency, topics,
   risk + reasons, churn flag, summary. Metered as the billable unit.
3. **Automate** — `actions/engine.py` evaluates declarative rules
   (AND-combined conditions over canonical fields) and executes actions:
   `webhook`, `alert`, `draft_reply`, `tag`. Every execution is recorded in
   `action_runs` — the audit log is the customer's proof of work.
   - **Built-in system rule:** risk high/critical always alerts. Not
     configurable, not deletable.
   - **Safety gate (code, not prompt):** `draft_reply` with
     `auto_approve: true` still routes to human approval unless risk ≤ low AND
     sentiment ∈ {positive, neutral} AND the model's own `escalate_to_human`
     is false.
   - Action failures are recorded and never poison the pipeline.

## Intelligence layer (`sona/intelligence/`)

| Concern | Decision | Why |
|---|---|---|
| Output integrity | `messages.parse()` + Pydantic contracts for every call | Malformed output impossible by contract; model swaps are config |
| Cost | Static system prompts (taxonomy embedded) with `cache_control` | Marginal cost per signal ≈ the signal text |
| Tiers | `claude-haiku-4-5` enrich / `claude-opus-4-8` generate+synthesize | Volume work cheap; customer-facing quality premium |
| Synthesis | Opus with adaptive thinking over a compact counted digest | `/v1/ask` answers must be grounded; evidence IDs validated server-side against the tenant's own signals |
| Testability | Injectable client; `FakeIntelligence` in tests | Full suite runs offline |

**Inference economics:** enrichment ~$0.001/signal (Haiku, cached prompt);
reply drafting ~$0.006 when an automation requests it. At Growth pricing
($499 / 10k signals), inference is ~2-4% of revenue → ~95% gross margin.

## Benchmarks (`sona/benchmarks.py`) — the network effect

Nightly job aggregates enriched signals per `(industry, topic, period)`:
org count, signal count, mean sentiment, negative share. Privacy by
construction:

- Aggregates carry **no organization id** — raw tenant data never crosses the
  tenant boundary.
- **k-anonymity at read time**: a segment is published only when
  `org_count >= SONA_BENCHMARK_MIN_ORGS` (default 5). Thin segments exist in
  the table but are invisible until the network grows.

## Security model

- API keys: `sk_sona_` + 256-bit token, **sha256-hashed at rest**, returned
  exactly once at signup.
- Tenant isolation on every query (`organization_id`); cross-tenant access
  returns 404 (existence never leaks). Covered by tests.
- Signal content is untrusted input: it only ever appears in user turns,
  never in system prompts; `/v1/ask` evidence IDs are filtered against the
  tenant's own signals server-side.
- Automations fail closed: unknown condition fields/ops never match.

## Scaling path

| Stage | Bottleneck | Move |
|---|---|---|
| 0 → 1k orgs | none | current architecture (Postgres + 2 containers) |
| 1k → 10k | polling fan-out, sync enrichment | queue (Redis/SQS) between ingest and enrich; worker pool |
| 10k+ | inference throughput / cost | Anthropic Batches API for backfills (-50%); keep live path real-time |
| Big tenants | analytical queries | warehouse destinations (Snowflake/BigQuery sync) — roadmap |
