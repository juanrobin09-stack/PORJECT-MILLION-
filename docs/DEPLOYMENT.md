# Resona — Production Deployment

## Topology

Three components: **API** (uvicorn), **worker** (poller + scheduler), and
**Postgres**. The included `docker-compose.yml` runs all three; the same images
deploy to any container platform (Fly.io, Render, ECS, Cloud Run + Cloud SQL).

```bash
cp .env.example .env   # fill in secrets
docker compose up --build -d
```

## Required configuration

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Powers all analysis/drafting. Without it, ingestion works but reviews are stored unanalyzed (useful for staging). |
| `RESONA_DATABASE_URL` | `postgresql+psycopg://user:pass@host:5432/resona` in production |
| `RESONA_ALERT_WEBHOOK_URL` | Slack/Discord incoming-webhook for risk alerts |
| `GOOGLE_BUSINESS_API_KEY` / `TRUSTPILOT_API_KEY` | Enable connector polling; otherwise webhook-only ingestion |
| `STRIPE_SECRET_KEY` | Billing (metered usage export reads `usage_records`) |

Model tiers are overridable (`RESONA_MODEL_RESPONSE`, `RESONA_MODEL_TRIAGE`,
`RESONA_MODEL_INSIGHTS`) — e.g. drop the response model to `claude-sonnet-4-6`
for a cheaper tier without code changes.

## Production checklist

- [ ] Postgres with automated backups (the DB is the business)
- [ ] TLS termination at the load balancer; API serves plain HTTP internally
- [ ] Set `RESONA_ENV=production`
- [ ] Anthropic API key scoped to a dedicated workspace; spend alerts on
- [ ] Alert webhook wired to an on-call channel, not a graveyard channel
- [ ] Uptime check on `GET /health`
- [ ] Log aggregation: both processes log structured lines to stdout
- [ ] Run `pytest` in CI (already wired in `.github/workflows/ci.yml`)

## Operations

**Database migrations** — schema is created via `init_db()` at startup. Before
the first breaking schema change, adopt Alembic (`alembic init`, autogenerate
against `app.database.Base`).

**Cost monitoring** — the dominant variable cost is Opus drafting. Watch the
Anthropic console per-workspace; the prompt-cache hit rate should stay >90%
once traffic is steady (system prompts are static by design — keep them that
way; see comments in `app/ai/prompts.py`).

**Scaling** — API replicas scale freely. Run exactly one worker until location
count demands partitioning (see ARCHITECTURE.md → Scaling path).

**Quota resets** — usage is computed from `usage_records` per calendar month
(UTC); no cron needed.
