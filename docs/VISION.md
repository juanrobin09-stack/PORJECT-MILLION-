# Sona — Vision & Investment Memo

## Why we killed Resona (the v1 post-mortem)

V1 of this repository was Resona: an AI agent that answered customer reviews.
It worked, it was sellable, and it was the wrong company. A ruthless look:

| Resona (v1) | Verdict |
|---|---|
| Review *response* automation | A **feature**. Birdeye, Podium, every POS and booking system will bundle it within 24 months. |
| Value lives in the output (the reply) | Output is fungible; the customer keeps nothing if they leave. Switching cost ≈ 0. |
| Per-location SMB pricing | Real but capped market; high churn segment; no path to $100M ARR without a platform. |
| Data: each tenant's reviews, siloed | No compounding. Tenant #1,000 gets the same product as tenant #1. |

One thing in v1 was genuinely valuable: the pipeline that converts unstructured
customer feedback into **validated, structured, canonical data** — with
safety-gated autonomous action on top. That is not a feature. Generalized, it
is a **layer**: the system of record for what customers are saying, across
every channel, for any business.

So v2 deletes the app and keeps the layer. Resona's reply-writing survives as
the first *module* on the platform — proof that modules can be built, not the
point of the company.

## What Sona is

**Sona is the customer signal layer** — the Segment/Plaid of customer
feedback. Businesses route every feedback channel through Sona:

```
reviews · NPS verbatims · support tickets · chats · surveys · social mentions
                       │
                       ▼
        ┌──────────────────────────────┐
        │   ONE CANONICAL SIGNAL SCHEMA │   ← the strategic asset
        │   + AI enrichment             │
        │   (sentiment, intent, topics  │
        │    on ONE shared taxonomy,    │
        │    risk, churn, language)     │
        └──────┬───────────┬───────────┘
               │           │
        AUTOMATIONS     ANSWERS & BENCHMARKS
        (webhooks to    ("what do customers
         their stack,     complain about?" /
         alerts, replies,  "how do I compare
         tags)             to my industry?")
```

The product is an **API-first platform** with four primitives:

1. **Signals** — ingest anything via connectors or one POST; idempotent,
   canonical, enriched within seconds.
2. **Automations** — declarative rules over the canonical schema firing real
   actions (webhooks into their CRM/Slack/ticketing, alerts, AI replies, tags).
   Because the schema is canonical, one rule spans every channel.
3. **Ask** — natural-language questions answered over the tenant's enriched
   signals, with evidence IDs. "What do detractors mention that promoters
   don't?" is an API call.
4. **Benchmarks** — anonymized, k-anonymous industry aggregates on the shared
   taxonomy. *Only possible because every tenant speaks the same schema.*

## Why this clears the "100x" bar

**Better with data.** The canonical taxonomy is the network effect. Every new
tenant makes benchmarks denser for all tenants; unmapped topic labels are
harvested to grow the taxonomy itself. None of this is replicable without the
customer base — a model can be copied, an installed base speaking one schema
cannot.

**Harder to leave every month.** Sona accumulates the tenant's full signal
history (the system of record), their automation graph wired into their own
stack, and their tuned brand voice. Leaving means losing history, rewiring
integrations, and going blind on benchmarks.

**Automates high-value work.** Triage, routing, escalation, response, and
analysis of customer feedback is skilled labor done badly at every company on
earth — and the canonical schema lets one platform automate it for all of them.

**Extensible without rebuild.** Channels = connectors (one interface). Outputs
= actions (one interface). Verticals = modules (reputation today; support
insights, product intelligence, CX compliance next). The schema is the
constitution; everything else is plug-ins.

**Sells globally, prices like infrastructure.** Volume-based plans
($0 dev → $499 → $1,990 → enterprise) with usage expansion built in, no
per-seat friction, language-agnostic by design (enrichment detects and
mirrors language).

## The wedge, unchanged

You don't sell a "signal layer" to a 12-location restaurant group — you sell
"every review answered in your voice, and you'll know first if something
dangerous appears." The reputation module is the wedge; the platform is what
they're standing on a year later when every channel flows through Sona and
the Monday question is answered by `/v1/ask`.

## End state (10 years)

Sona is where "what are customers saying?" is answered — the way Stripe is
where payments happen. Customer-feedback data that doesn't flow through a
canonical signal layer will look as archaic as payments without a payments
API. The taxonomy is the industry standard; the benchmark dataset is the
moat nobody can buy.
