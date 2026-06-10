# Sona — 12-Month Roadmap

Filter for every item: *does it increase taxonomy density, switching cost, or
signal volume?* If not, it doesn't ship.

## Now → Month 3 — Wedge live

- [x] Canonical signal schema + taxonomy v2026.06 (the constitution)
- [x] Enrichment pipeline (structured outputs, tiered models, metering)
- [x] Automation engine (webhook/alert/draft_reply/tag) + audit log + code-level safety gates
- [x] `/v1/ask` synthesis with evidence validation
- [x] Cross-tenant benchmarks with k-anonymity
- [x] Reputation module (brand voice + approval workflow) — the wedge
- [x] API keys hashed at rest
- [ ] Alembic migrations
- [ ] Stripe metered billing on `usage_records`
- [ ] Publisher worker: push approved replies via Google Business Profile API
- [ ] Approval-inbox web app (thin client; API already complete)
- [ ] 20 design partners on the reputation wedge

## Months 3–6 — More channels per tenant

- [ ] Connectors: Yelp, Facebook, App Store / Play Store, Zendesk, Intercom,
      Typeform/NPS tools (each = one `SignalConnector` implementation)
- [ ] Free **Signal Audit** PLG tool (reuses the enrichment engine)
- [ ] Webhook signature verification + retries with backoff (delivery SLO)
- [ ] Queue between ingest and enrich (Redis) — removes the sync bottleneck
- [ ] Taxonomy council process: promote high-frequency `raw_topics` into the
      canonical taxonomy monthly (data-driven vocabulary growth)
- [ ] Multi-user orgs, roles, audit trail; SOC 2 Type I groundwork

## Months 6–9 — The data products

- [ ] **Benchmarks GA** once ≥5-org density in 3 industries; benchmark deltas
      in the weekly digest ("you vs. category, this month")
- [ ] Anomaly detection: complaint-rate spikes per topic (review-bombing,
      product regressions) → built-in alert rule
- [ ] Warehouse destinations: Snowflake / BigQuery sync (enterprise pull)
- [ ] `/v1/ask` v2: cross-period comparisons, saved questions, scheduled
      answers delivered to Slack

## Months 9–12 — Layer economics

- [ ] Modules SDK: third parties build vertical modules (support insights,
      product intelligence) on the signal store — rev share
- [ ] Agency white-label (sub-orgs, theming, consolidated billing)
- [ ] Enterprise: SSO/SAML, data residency, DPAs, retention policies
- [ ] Industry benchmark reports (anonymized, k-anonymous) as marketing +
      standalone data product

## Principles

1. The schema is the constitution; channels, actions, and modules are plug-ins.
2. Safety gates live in code, never only in prompts.
3. Raw tenant data never crosses the tenant boundary — aggregates only, above k.
4. Signals are never dropped; quota gates enrichment, not storage.
