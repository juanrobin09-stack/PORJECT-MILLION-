"""Structured-output contracts between Sona and the models.

These Pydantic schemas ARE the API of the intelligence layer: every model call
goes through `messages.parse()` against one of them, so malformed output is
impossible by contract and model swaps are config changes.
"""

from pydantic import BaseModel, Field

from sona.models import Intent, RiskLevel, Sentiment, Urgency


class SignalEnrichment(BaseModel):
    """What the enrichment model must return for every signal."""

    sentiment: Sentiment
    sentiment_score: float = Field(ge=-1, le=1)
    language: str = Field(description="BCP-47 code of the signal text, e.g. 'en', 'fr'")
    intent: Intent
    urgency: Urgency
    topics: list[str] = Field(
        max_length=8,
        description="Topic labels — use canonical taxonomy slugs whenever one fits",
    )
    risk_level: RiskLevel
    risk_reasons: list[str] = Field(
        default=[],
        description="Concrete reasons only: legal threat, health/safety claim, "
        "discrimination allegation, regulator mention, viral potential, fraud claim",
    )
    churn_risk: bool = Field(description="True if the customer signals they are leaving")
    summary: str = Field(description="One neutral sentence")


class DraftedReply(BaseModel):
    """Public reply drafted by the reputation module."""

    reply_text: str
    addresses_points: list[str] = Field(default=[])
    escalate_to_human: bool = Field(
        description="True when no reply should go out without human review"
    )
    escalation_reason: str = Field(default="")


class SynthesizedAnswer(BaseModel):
    """Answer to a natural-language question over the tenant's signals."""

    answer: str = Field(description="Direct answer grounded in the provided signals")
    evidence_signal_ids: list[int] = Field(
        default=[], description="IDs of the signals that support the answer"
    )
    confidence: str = Field(description="high | medium | low — based on evidence coverage")
    caveats: str = Field(default="", description="What the data cannot answer")
