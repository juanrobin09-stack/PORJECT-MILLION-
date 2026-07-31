# Sona — Business Plan

## Category

**Customer signal infrastructure.** The system of record for what customers
say, the way Segment is for behavioral events and Plaid is for bank data.
Incumbent budgets exist: Qualtrics went private at $12.5B, Medallia at $6.4B —
survey-era "experience management" suites built before LLMs could read. The
AI-native, API-first replacement slot is open.

## The problem, restated as infrastructure

Companies already pay for the symptoms separately: reputation tools for
reviews, support analytics for tickets, survey tools for NPS, social
listening for mentions — five dashboards, five vocabularies, zero shared
truth, and none of it actions anything. The data layer underneath is missing.
Sona is that layer: one schema, one taxonomy, one automation engine, one
question-answering surface.

## Why Sona wins (the moat, concretely)

1. **The taxonomy network effect.** Every tenant's signals are normalized to
   one canonical topic vocabulary. That yields the only dataset of its kind:
   cross-company, cross-channel, comparable. Benchmarks ("your billing
   complaint rate is 2.1× your industry") get denser with every customer and
   cannot be bought or scraped. Copying the software does not copy the moat.
2. **System-of-record gravity.** Tenants accumulate signal history,
   automation graphs wired into their own stack, and tuned brand voices.
   Churning means losing memory, rewiring integrations, going blind on
   benchmarks.
3. **Margin structure.** Tiered inference (Haiku enrichment ~$0.001/signal,
   Opus only where customers see the words) on cached prompts → ~95% gross
   margin, which funds a price point incumbents structurally can't follow.
4. **Extensibility without rebuild.** Channels are connectors, outputs are
   actions, verticals are modules. R&D compounds on one schema instead of
   fragmenting across products.

## Pricing — volume-based, like infrastructure

| Plan | $/mo | Signals/mo | For |
|---|---|---|---|
| Developer | $0 | 500 | PLG entry; every integration starts free |
| Growth | $499 | 10,000 | Multi-location SMB groups, mid-market CX teams |
| Scale | $1,990 | 100,000 | Brands, marketplaces, support orgs |
| Enterprise | custom | unlimited | SSO, warehouse sync, DPAs, SLA |

Over-quota signals are **stored raw, never dropped**, and enriched
retroactively on upgrade — the upgrade is always one click from visible value.
Expansion is automatic: feedback volume grows with the customer's business,
and each new channel routed through Sona increases volume *and* switching
cost simultaneously.

**Unit economics:** COGS ≈ inference (~$0.001–0.007/signal) + hosting → <5%
of revenue at every tier. A Growth customer at full quota costs <$25/mo to
serve against $499.

## Go-to-market — wedge, then layer

**Phase 1 (0–3 mo): the reputation wedge.** Sell the v1 outcome — "every
review answered, in your voice, within the hour, risk caught first" — to
multi-location consumer businesses via 20 design partners. They don't buy a
platform; they buy a result that the platform delivers through one module.

**Phase 2 (3–9 mo): land more channels per tenant.** The expansion motion is
internal: "your reviews are flowing — route your NPS and support tickets
through the same pipe and `/v1/ask` starts answering your Monday meeting."
Free Signal Audit tool (paste a listing, get an AI scorecard) as PLG top of
funnel; developer-plan API as the bottoms-up channel.

**Phase 3 (9+ mo): the benchmark unlock.** At ~50 orgs per industry segment,
benchmarks turn on (k-anonymity satisfied) and become the marquee feature no
competitor can ship on day one — and the reason category leaders join: the
data is where their peers are.

**Channel:** agencies and CX consultancies white-label modules on Sona's API
(rev share) — they bring tenants; tenants bring taxonomy density.

## Market sizing

Bottom-up on the wedge alone: ~30M reviewable locations NA+EU; 1% penetration
at blended $150/mo ≈ $540M ARR. The layer expands TAM to every company with
customers: CX/feedback software spend is $15B+ and shifting to AI-native
tooling. The benchmark dataset is additionally monetizable (industry reports,
data partnerships) without touching tenant-level data.

## Risks

| Risk | Mitigation |
|---|---|
| "Schema-washing" by incumbents | Their per-product data models are load-bearing legacy; our canonical schema is the founding constraint, not a retrofit |
| Platform API access (Google/era of walled gardens) | Webhook-first ingestion; the layer is channel-agnostic by design — no single pipe is existential |
| LLM commoditization | Good — enrichment costs fall, margins rise; the moat is the installed base + taxonomy data, not the model |
| Privacy/regulatory | Aggregates carry no tenant IDs; k-anonymity at read time; per-tenant data residency on the enterprise tier |
| One bad auto-reply | Safety gates in code (risk + sentiment + model escalation flag); approval-first defaults; full action audit log |

## KPIs

North star: **signals enriched per week** (the volume of the layer).
Moat health: channels per tenant (>2 = locked in), taxonomy coverage
(% signals with ≥1 canonical topic), benchmark-eligible segments.
Commercial: net revenue retention (target >130% — volume growth + channel
expansion), gross margin (>90%), `/v1/ask` weekly active orgs.
