# Sona — Production Deployment

## Topology

Three components: **API** (uvicorn), **worker** (connector polling + nightly
benchmarks), **Postgres**. `docker-compose.yml` runs all three; the same
images deploy to any container platform (Fly.io, Render, ECS, Cloud Run +
Cloud SQL).

```bash
cp .env.example .env   # fill in secrets
docker compose up --build -d
```

## Required configuration

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Powers enrichment, replies, and `/v1/ask`. Without it, ingestion still works and signals are stored raw (useful for staging). |
| `SONA_DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/sona` in production |
| `GOOGLE_BUSINESS_API_KEY` / `TRUSTPILOT_API_KEY` | Enable connector polling; otherwise ingest-API only |
| `SONA_BENCHMARK_MIN_ORGS` | k-anonymity threshold (default 5 — do not lower in production) |

Model tiers are env-overridable (`SONA_MODEL_ENRICH`, `SONA_MODEL_GENERATE`)
— cost/quality is a config change, never a deploy.

## Production checklist

- [ ] Postgres with automated backups (the signal store is the business)
- [ ] TLS at the load balancer; `SONA_ENV=production`
- [ ] Anthropic key in a dedicated workspace; spend alerts on
- [ ] Uptime check on `GET /health`
- [ ] Log aggregation (both processes log structured lines to stdout)
- [ ] CI green (`.github/workflows/ci.yml` runs the 24-test suite)

## Operations

**Migrations** — schema is created by `init_db()` at startup; adopt Alembic
before the first breaking change (roadmap, month 1-3).

**Cost** — the dominant variable cost is Opus generation (replies + ask).
Watch prompt-cache hit rate (`usage.cache_read_input_tokens` in the Anthropic
console) — system prompts are static by design; keep them that way (see notes
in `sona/intelligence/prompts.py`). Enrichment on Haiku is ~$0.001/signal.

**Scaling** — API replicas scale freely; one worker until source count
demands partitioning (then: queue + worker pool, see ARCHITECTURE.md).

**Quotas** — computed from `usage_records` per calendar month (UTC); no cron.
Over-quota signals are stored raw and enriched retroactively on upgrade.

**Benchmarks** — recomputed nightly (04:00 UTC by default); safe to re-run
ad hoc: `python -c "from sona.database import SessionLocal; from sona.benchmarks import compute_benchmarks; compute_benchmarks(SessionLocal())"`.
