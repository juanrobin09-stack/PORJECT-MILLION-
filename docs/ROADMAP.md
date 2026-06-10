# Resona — 12-Month Roadmap

## Now → Month 3 — Prove the wedge

- [x] Core pipeline: ingest → analyze → draft → route (this repo)
- [x] Brand-voice profiles, approval workflow, risk alerts, weekly insights
- [x] Google/Trustpilot connectors + webhook ingestion
- [ ] **Hash API keys at rest**; key rotation endpoint
- [ ] Alembic migrations
- [ ] Publisher worker: push approved replies via Google Business Profile API
- [ ] Minimal web dashboard (approval inbox + voice editor) — the API already
      supports everything; this is a thin Next.js client
- [ ] Stripe checkout + metered usage export
- [ ] 20 design partners live

## Months 3–6 — Product-led growth

- [ ] **Free Reputation Audit** tool (the PLG wedge — reuses the analysis engine)
- [ ] Yelp, Facebook, TripAdvisor, App Store / Play Store connectors
- [ ] Response quality learning loop: feed approved-with-edits diffs back into
      per-org voice profiles ("you always soften refund language — adopted")
- [ ] Multi-user orgs with roles (owner / manager / approver)
- [ ] Email digest delivery of the Monday brief
- [ ] SOC 2 Type I groundwork

## Months 6–9 — The data moat

- [ ] **Category benchmarking**: "your wait-time complaint rate vs. category
      median" — requires cross-tenant anonymized aggregation layer
- [ ] Review-bombing detection (burst anomaly detection on rating velocity)
- [ ] Competitive watch: track competitors' public reviews for sales-trigger
      insights
- [ ] Batches API path for backfill/bulk analysis at 50% inference cost

## Months 9–12 — Move upmarket

- [ ] Agency white-label (theming, sub-orgs, rev-share billing)
- [ ] Enterprise SSO (SAML/OIDC), audit log export
- [ ] Survey + private-feedback ingestion (NPS verbatims through the same
      pipeline — expands TAM beyond public reviews)
- [ ] In-context reply suggestions browser extension (for platforms with no API)

## Principles

1. The pipeline is the product; every feature must feed it or feed off it.
2. Safety gates live in code, never only in prompts.
3. Anything that increases drafts-approved-without-edit ships first.
