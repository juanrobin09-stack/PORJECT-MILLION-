<p align="center">
  <img src="web/logo.svg" alt="Resona" width="96" />
</p>

<h1 align="center">Resona — The AI Reputation Engine</h1>

<p align="center">
  <strong>Every review answered. Every insight captured. Every risk caught.</strong><br/>
  Autonomous review response, sentiment intelligence, and reputation alerting for multi-location businesses.
</p>

---

## What Resona is

Online reviews are the single highest-leverage marketing surface for local and consumer businesses: 93% of consumers read reviews before buying, and businesses that respond to reviews earn measurably higher ratings and conversion. Yet most businesses answer fewer than 1 in 4 reviews, because doing it well — on-brand, in the customer's language, within hours — does not scale with humans.

Resona is an autonomous agent that does it for them:

1. **Ingests** reviews continuously from Google Business Profile, Trustpilot, and any source via webhook.
2. **Understands** each review with Claude — sentiment, topics, urgency, churn risk, and legally sensitive content — as validated, structured data.
3. **Responds** in the business's own voice, governed by a per-brand voice profile and configurable approval workflow (auto-publish, human-approve, or draft-only).
4. **Alerts** owners in real time when a review signals reputation risk (health/safety claims, legal threats, review-bombing patterns, sudden rating drops).
5. **Reports** weekly executive insights: what customers love, what's breaking, which locations are slipping, and what to fix first.

It is sold as a B2B SaaS with per-location recurring pricing. Margins are structurally high: the unit of work (one review) costs fractions of a cent in inference and replaces minutes of human labor priced at dollars.

## Quickstart (local)

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env          # add your ANTHROPIC_API_KEY

# 3. Run the API
uvicorn app.main:app --reload

# 4. Open the docs
open http://localhost:8000/docs
```

Or with Docker:

```bash
docker compose up --build
```

### 60-second demo

```bash
# Create an organization (returns an API key)
curl -s -X POST localhost:8000/v1/organizations \
  -H 'Content-Type: application/json' \
  -d '{"name": "Bluebird Coffee", "plan": "growth"}'

# Add a location
curl -s -X POST localhost:8000/v1/locations \
  -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
  -d '{"name": "Bluebird Coffee — Mission St", "platform_ids": {"google": "ChIJexample"}}'

# Ingest a review (webhook or connector does this automatically in production)
curl -s -X POST localhost:8000/v1/reviews/ingest \
  -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
  -d '{"location_id": 1, "platform": "google", "external_id": "r-1001",
       "author": "Dana M.", "rating": 2,
       "text": "Waited 25 minutes for a latte and the barista was rude about it."}'

# Resona analyzes it and drafts a response automatically. Fetch the draft:
curl -s localhost:8000/v1/responses?status=pending_approval -H "Authorization: Bearer $API_KEY"
```

## Repository layout

```
app/                 FastAPI application
  ai/                Claude integration: prompts, structured analysis, response engine
  connectors/        Review-source connectors (Google, Trustpilot, generic webhook)
  routers/           HTTP API (organizations, locations, reviews, responses, insights, billing)
  services/          Domain logic: pipeline, alerting, insights, usage metering
  worker.py          Background poller + weekly insight scheduler
tests/               Pytest suite (AI layer fully mocked — no network needed)
web/                 Marketing landing page (static, deployable to any CDN)
docs/                Architecture, API reference, business plan, brand, deployment, roadmap
```

## Documentation

| Doc | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data model, AI pipeline, scaling path |
| [docs/API.md](docs/API.md) | Full HTTP API reference |
| [docs/BUSINESS.md](docs/BUSINESS.md) | Market, pricing, unit economics, go-to-market plan |
| [docs/BRAND.md](docs/BRAND.md) | Identity, voice, positioning, launch copy |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment (Docker, Postgres, secrets) |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 12-month product roadmap |

## Tech

Python 3.11 · FastAPI · SQLAlchemy (SQLite dev / Postgres prod) · Anthropic Claude API (Opus 4.8 + Haiku 4.5) · APScheduler · Stripe (billing) · Docker

## License

Proprietary. See [LICENSE](LICENSE).
