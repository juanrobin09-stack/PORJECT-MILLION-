"""The canonical topic taxonomy — Sona's shared vocabulary.

Every signal from every tenant is mapped onto this single taxonomy. That is
the precondition for the platform's network effect: because "wait time" means
the same thing for a coffee chain in Lyon and a dental group in Austin,
cross-tenant benchmarking ("your wait-time complaint rate is 2.3x the category
median") is possible — and impossible to replicate without the data.

The taxonomy is versioned and append-only. Models map free-form labels onto
the nearest canonical slug; unmapped labels are kept verbatim in
`raw_topics` and reviewed for promotion into the taxonomy (taxonomy growth is
itself driven by accumulated data).
"""

TAXONOMY_VERSION = "2026.06"

# slug -> human label. Slugs are stable identifiers; labels can be localized.
CANONICAL_TOPICS: dict[str, str] = {
    # Service & people
    "wait-time": "Wait time",
    "staff-friendliness": "Staff friendliness",
    "staff-competence": "Staff competence",
    "communication": "Communication",
    "support-responsiveness": "Support responsiveness",
    "appointment-scheduling": "Appointment & scheduling",
    # Product & quality
    "product-quality": "Product quality",
    "food-quality": "Food & beverage quality",
    "consistency": "Consistency",
    "selection-availability": "Selection & availability",
    "freshness": "Freshness",
    "ease-of-use": "Ease of use",
    "reliability": "Reliability & uptime",
    "performance": "Performance & speed",
    "missing-feature": "Missing feature",
    "defect": "Defect / bug",
    # Money
    "pricing": "Pricing & value",
    "billing": "Billing & charges",
    "refunds": "Refunds & cancellations",
    "hidden-fees": "Hidden fees",
    # Logistics
    "delivery": "Delivery & shipping",
    "order-accuracy": "Order accuracy",
    "packaging": "Packaging",
    "returns": "Returns process",
    # Environment
    "cleanliness": "Cleanliness & hygiene",
    "ambiance": "Ambiance & comfort",
    "parking-access": "Parking & accessibility",
    "safety": "Safety",
    "crowding": "Crowding & capacity",
    # Digital
    "website-app": "Website / app experience",
    "checkout": "Checkout & payment flow",
    "account-login": "Account & login",
    "onboarding": "Onboarding",
    "documentation": "Documentation & help content",
    "privacy-data": "Privacy & data handling",
    # Relationship
    "loyalty-rewards": "Loyalty & rewards",
    "policy": "Policies & terms",
    "trust-integrity": "Trust & integrity",
    "accessibility-inclusion": "Accessibility & inclusion",
}

# Common synonyms normalized in code, so taxonomy discipline does not depend
# entirely on the model. Lowercased keys.
SYNONYMS: dict[str, str] = {
    "wait time": "wait-time",
    "waiting time": "wait-time",
    "queue": "wait-time",
    "slow service": "wait-time",
    "speed of service": "wait-time",
    "rude staff": "staff-friendliness",
    "friendly staff": "staff-friendliness",
    "customer service": "support-responsiveness",
    "price": "pricing",
    "expensive": "pricing",
    "value for money": "pricing",
    "overcharged": "billing",
    "refund": "refunds",
    "shipping": "delivery",
    "late delivery": "delivery",
    "dirty": "cleanliness",
    "hygiene": "cleanliness",
    "bug": "defect",
    "crash": "defect",
    "downtime": "reliability",
    "uptime": "reliability",
    "app": "website-app",
    "website": "website-app",
    "login": "account-login",
    "food poisoning": "safety",
    "injury": "safety",
}


def normalize_topic(label: str) -> str | None:
    """Map a free-form label to a canonical slug, or None when unmapped."""
    key = label.strip().lower()
    slug = key.replace(" ", "-").replace("&", "and")
    if slug in CANONICAL_TOPICS:
        return slug
    if key in SYNONYMS:
        return SYNONYMS[key]
    return None


def normalize_topics(labels: list[str]) -> tuple[list[str], list[str]]:
    """Returns (canonical_slugs, unmapped_raw_labels) — deduplicated, ordered."""
    canonical: list[str] = []
    unmapped: list[str] = []
    for label in labels:
        slug = normalize_topic(label)
        if slug is not None:
            if slug not in canonical:
                canonical.append(slug)
        elif label.strip() and label.strip().lower() not in unmapped:
            unmapped.append(label.strip().lower())
    return canonical, unmapped


def taxonomy_prompt_block() -> str:
    """The taxonomy as injected into the enrichment system prompt (static —
    safe to cache)."""
    lines = [f"- {slug}: {label}" for slug, label in CANONICAL_TOPICS.items()]
    return (
        f"CANONICAL TOPIC TAXONOMY (version {TAXONOMY_VERSION}) — assign topics "
        "using these slugs whenever one fits; only invent a free-form label when "
        "nothing fits:\n" + "\n".join(lines)
    )
