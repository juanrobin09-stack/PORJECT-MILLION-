# Resona — Business Plan

## The problem (and why it's worth money)

- **Reviews decide revenue.** ~93% of consumers consult reviews before buying;
  a one-star rating change moves revenue 5–9% for local businesses (Harvard
  Business School, Luca). Responding to reviews measurably improves ratings and
  conversion — Google itself tells businesses to respond.
- **Almost nobody does it well.** Industry studies put response rates below
  25%. The job is unbounded (reviews arrive 24/7), skilled (one bad reply can
  go viral), and repetitive — the worst possible shape for human labor and the
  best possible shape for an AI agent.
- **The buyer already pays for worse.** Reputation-management suites
  (Birdeye, Podium, Reputation.com) charge $300–600/location/month for
  dashboards plus template responses. Their AI is bolted on; ours *is* the
  product, at a third of the price.

## Product thesis

Resona sells an **outcome** — "every review answered, in your voice, within the
hour, and you'll know before anyone else if something dangerous appears" — not
a dashboard. The wedge is response automation (immediate, visible value); the
moat compounds from there:

1. **Voice lock-in** — each org's tuned brand-voice profile and approval
   history make replies steadily better and switching costly.
2. **Data flywheel** — structured topic/sentiment data across thousands of
   locations becomes benchmarking ("your wait-time complaints are 2.3× the
   category median"), a feature incumbents can't copy without our data.
3. **Workflow gravity** — once risk alerts page the owner and the Monday brief
   runs the ops meeting, Resona is infrastructure, not a tool.

## Market

- **TAM:** ~200M reviews/year across ~30M reviewable business locations in
  NA+EU. At a blended $80/location/month, serviceable market ≈ $8–10B/yr.
- **Beachhead ICP:** multi-location consumer businesses, 3–50 locations —
  restaurant groups, dental/med-spa chains, gyms, auto services, hospitality.
  They have acute pain (volume × brand risk), a budget line (marketing), and
  one decision-maker (owner/CMO).

## Pricing & unit economics

| Plan | $/location/mo | AI responses | Differentiators |
|---|---|---|---|
| Starter | $49 | 150 | analysis + approval workflow |
| Growth | $99 | 600 | + weekly insights, auto-publish, churn flags |
| Scale | $249 | unlimited | + real-time risk alerts, API, SLA |

- **COGS:** < $0.01 inference per review-response pair (Haiku analysis + Opus
  draft on cached prompts) + hosting ≈ **< 5% of revenue → ~92% gross margin.**
- **Value anchor:** a manager's thoughtful reply costs ~6 min × $25/hr ≈ $2.50.
  Growth plan prices the equivalent of 600 replies ($1,500 of labor) at $99.
- **Expansion built-in:** pricing is per location; customers grow our ACV by
  opening stores. Quota upsells convert automatically (drafting pauses at the
  cap; analysis keeps running so the upgrade value stays visible).

**Illustrative P&L at 1,000 customers × 4 locations × $99:**
ARR ≈ $4.75M · gross margin ~92% · CAC payback < 4 months at $1,200 blended
CAC (self-serve + light inside sales).

## Go-to-market

**Phase 1 — Prove (months 0–3):** 20 design partners from the founder network
at 50% off forever in exchange for case-study rights. Success metric: response
rate from <25% → >95%, and at least 3 documented "the alert caught it first"
stories.

**Phase 2 — Product-led (months 3–9):**
- *The Reputation Audit*: free tool — paste your Google listing, get an AI
  scorecard of your unanswered reviews and what they're costing you. The
  audit's "fix this now" button is the trial signup. Built on the existing
  analysis endpoint; near-zero marginal cost.
- Content engine: weekly teardown of real (anonymized) review disasters and
  ideal responses — the niche is starving for specifics.
- Marketplace listings: Google Business Profile & Trustpilot app directories.

**Phase 3 — Sales-assisted (months 9+):** outbound to 10–50-location groups
using their own public unanswered reviews as the opener ("here are 14 reviews
from last week your competitors answered and you didn't — here's what we'd
have said"). Partner channel: digital agencies white-label Resona for their
local-business books (20% rev share).

## Why now

1. Frontier models crossed the quality bar where AI replies are *better* than
   median human replies (tone discipline, legal caution, language mirroring).
2. Inference costs collapsed — prompt caching + a cheap-triage/premium-writer
   split makes <$0.01/review possible, which makes $49 entry pricing possible.
3. Incumbents carry dashboard-era cost structures and pricing; they cannot
   reprice to $49 without destroying their own revenue base.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Platform API access tightens (Google) | Webhook-first ingestion; approval-mode keeps a human publishing where APIs are restricted; multi-platform from day one |
| One bad auto-published reply goes viral | Hard-coded safety gates (risk + sentiment + AI's own escalation flag) before auto-publish; approval mode is the default |
| Incumbents add comparable AI | Compete on price (their structure can't follow), voice quality, and the benchmarking flywheel |
| Model dependency | Engine is provider-thin (one class); structured-output contracts make model swaps a config change |

## KPIs

North star: **% of customer reviews answered within 1 hour.**
Supporting: drafts approved without edit (>80% target — proxy for voice
quality), weekly active approvers, alert precision, net revenue retention
(target >120% via location growth), inference cost / revenue (<6%).
