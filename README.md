<p align="center">
  <img src="web/logo.svg" alt="Sona" width="96" />
</p>

<h1 align="center">Sona — The Customer Signal Layer</h1>

<p align="center">
  <strong>One schema for everything your customers say. Intelligence, automation, and benchmarks on top.</strong>
</p>

---

## What Sona is

Every company is told what's wrong with it every day — in reviews, NPS
verbatims, support tickets, chats, surveys, and social mentions. That feedback
is scattered, unstructured, unanswered, and unusable. Sona is the
infrastructure layer that fixes this:

1. **One canonical schema.** Every piece of feedback from every channel becomes
   a `Signal` — same shape, same vocabulary, forever queryable.
2. **AI enrichment.** Each signal is enriched within seconds: sentiment, intent,
   urgency, churn risk, legal/safety risk, language, and topics mapped onto a
   single cross-industry taxonomy.
3. **Automations.** Declarative rules over the canonical schema fire real
   actions: webhooks into your stack, alerts, on-brand AI replies (with a
   code-enforced safety gate), tags. One rule works across every channel.
4. **Ask.** Natural-language questions over your signals, answered with
   evidence: `POST /v1/ask {"question": "What do detractors mention that
   promoters don't?"}`.
5. **Benchmarks.** Because all tenants speak one taxonomy, Sona computes
   anonymized industry benchmarks (k-anonymity enforced): *"your wait-time
   complaint rate vs. your category"* — data no single company can have alone.

The **reputation module** (brand-voice reply drafting + approval workflow) is
the first vertical module on the platform and the commercial wedge.

## Quickstart

```bash
pip install -e ".[dev]"
cp .env.example .env          # add ANTHROPIC_API_KEY
uvicorn sona.main:app --reload
open http://localhost:8000/docs
```

Or: `docker compose up --build` (API + worker + Postgres).

### 90-second tour

```bash
# Sign up (the API key is returned once; only its hash is stored)
curl -s -X POST localhost:8000/v1/organizations \
  -H 'Content-Type: application/json' \
  -d '{"name": "Bluebird Coffee", "industry": "food & beverage", "plan": "growth"}'

# Create a source and ingest a signal — any channel, one endpoint
curl -s -X POST localhost:8000/v1/sources \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"name": "Google — Mission St", "kind": "google"}'

curl -s -X POST localhost:8000/v1/signals \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"source_id": 1, "external_id": "r-1001", "kind": "review", "rating": 2,
       "author": {"name": "Dana M."},
       "content": "Waited 25 minutes for a latte and the barista was rude about it."}'

# Seconds later the signal is enriched. Wire an automation:
curl -s -X POST localhost:8000/v1/automations \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"name": "Reply to all reviews",
       "conditions": [{"field": "kind", "op": "eq", "value": "review"}],
       "action_type": "draft_reply", "action_config": {"auto_approve": false}}'

# Ask your customers anything
curl -s -X POST localhost:8000/v1/ask \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"question": "What is driving negative sentiment this month?"}'
```

## Repository layout

```
sona/
  core/taxonomy.py     The canonical topic taxonomy (the shared vocabulary)
  models.py            Signal-centric data model (orgs, sources, signals,
                       automations, action runs, drafts, benchmarks, usage)
  intelligence/        Claude engine: enrichment, reply drafting, synthesis
                       (structured outputs + prompt caching + model tiers)
  actions/engine.py    Automation rules + actions, with code-level safety gates
  pipeline.py          ingest -> enrich -> automate -> meter
  benchmarks.py        Cross-tenant k-anonymous aggregates (the network effect)
  connectors/          Connector SDK + Google/Trustpilot connectors
  api/                 FastAPI surface (signals, ask, automations, benchmarks,
                       reputation module)
  worker.py            Connector polling + nightly benchmark recompute
tests/                 24 tests, AI fully mocked — runs with no network
docs/                  Vision/memo, architecture, API, business, brand, ops
web/                   Marketing site
```

## Documentation

| Doc | Contents |
|---|---|
| [docs/VISION.md](docs/VISION.md) | The investment memo — why v1 was killed and what Sona is |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, schema, AI economics, scaling |
| [docs/API.md](docs/API.md) | Full HTTP API reference |
| [docs/BUSINESS.md](docs/BUSINESS.md) | Market, pricing, moat, go-to-market |
| [docs/BRAND.md](docs/BRAND.md) | Identity and launch copy |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production operations |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 12-month plan |

## Tech

Python 3.11 · FastAPI · SQLAlchemy (SQLite dev / Postgres prod) · Anthropic
Claude (Haiku 4.5 enrichment / Opus 4.8 generation, structured outputs, prompt
caching) · APScheduler · Docker

## License

Proprietary. See [LICENSE](LICENSE).
