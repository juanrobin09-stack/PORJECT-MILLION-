"""Sona data model.

The center of gravity is the Signal: one canonical record for ANY piece of
customer feedback (review, NPS verbatim, support ticket, chat, survey, social
mention). Everything else — enrichment, automations, drafts, benchmarks — hangs
off it. This is what makes Sona a layer rather than an app: new channels add
connectors, new capabilities add actions; the schema does not move.
"""

import enum
import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sona.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def generate_api_key() -> str:
    return "sk_sona_" + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


# --- Plans: priced on signal volume, like infrastructure -----------------

class Plan(str, enum.Enum):
    developer = "developer"    # free — 500 signals/mo
    growth = "growth"          # $499/mo — 10k signals
    scale = "scale"            # $1,990/mo — 100k signals
    enterprise = "enterprise"  # custom — unlimited


PLAN_SIGNAL_QUOTA: dict[Plan, int | None] = {
    Plan.developer: 500,
    Plan.growth: 10_000,
    Plan.scale: 100_000,
    Plan.enterprise: None,
}


# --- Enums over the canonical signal schema -------------------------------

class SignalKind(str, enum.Enum):
    review = "review"
    nps = "nps"
    support_ticket = "support_ticket"
    chat = "chat"
    survey = "survey"
    social = "social"
    custom = "custom"


class Sentiment(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"
    mixed = "mixed"


class Intent(str, enum.Enum):
    praise = "praise"
    complaint = "complaint"
    question = "question"
    feature_request = "feature_request"
    bug_report = "bug_report"
    churn_signal = "churn_signal"
    legal_threat = "legal_threat"
    safety_issue = "safety_issue"
    other = "other"


class Urgency(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RiskLevel(str, enum.Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


RISK_ORDER = [RiskLevel.none, RiskLevel.low, RiskLevel.medium, RiskLevel.high, RiskLevel.critical]


# --- Tenancy ---------------------------------------------------------------

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str] = mapped_column(String(80), default="general")
    plan: Mapped[Plan] = mapped_column(Enum(Plan), default=Plan.developer)
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sources: Mapped[list["Source"]] = relationship(back_populates="organization")
    brand_voice: Mapped["BrandVoice | None"] = relationship(
        back_populates="organization", uselist=False
    )


class Source(Base):
    """Where signals come from: a Google listing, a Zendesk account, an NPS
    tool, or the customer's own systems via the ingest API."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(40), default="api")  # api|google|trustpilot|...
    config: Mapped[dict] = mapped_column(JSON, default=dict)      # connector-specific
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped[Organization] = relationship(back_populates="sources")


# --- The canonical signal ---------------------------------------------------

class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_source_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(160))
    kind: Mapped[SignalKind] = mapped_column(Enum(SignalKind), index=True)

    author: Mapped[dict] = mapped_column(JSON, default=dict)  # {name, customer_id?, ...}
    content: Mapped[str] = mapped_column(Text, default="")
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)      # 1-5 where applicable
    nps_score: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 0-10
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    # Enrichment (written once by the intelligence engine, read everywhere)
    sentiment: Mapped[Sentiment | None] = mapped_column(Enum(Sentiment), nullable=True, index=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    intent: Mapped[Intent | None] = mapped_column(Enum(Intent), nullable=True, index=True)
    urgency: Mapped[Urgency | None] = mapped_column(Enum(Urgency), nullable=True)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.none)
    risk_reasons: Mapped[list] = mapped_column(JSON, default=list)
    churn_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    topics: Mapped[list] = mapped_column(JSON, default=list)       # canonical taxonomy slugs
    raw_topics: Mapped[list] = mapped_column(JSON, default=list)   # model's verbatim labels
    summary: Mapped[str] = mapped_column(Text, default="")
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reply_draft: Mapped["ReplyDraft | None"] = relationship(back_populates="signal", uselist=False)


# --- Automations: declarative rules over enriched signals -------------------

class Automation(Base):
    __tablename__ = "automations"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # conditions: [{"field": "sentiment", "op": "eq", "value": "negative"}, ...] — AND-combined
    conditions: Mapped[list] = mapped_column(JSON, default=list)
    action_type: Mapped[str] = mapped_column(String(40))  # webhook | alert | draft_reply | tag
    action_config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ActionRun(Base):
    """Audit log of every action the platform took — the customer's proof of
    work, and ours."""

    __tablename__ = "action_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    automation_id: Mapped[int | None] = mapped_column(
        ForeignKey("automations.id"), nullable=True  # NULL = built-in system rule
    )
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))  # success | failed | skipped
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --- Reputation module (first vertical module on the platform) --------------

class ReplyStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    published = "published"
    rejected = "rejected"


class BrandVoice(Base):
    __tablename__ = "brand_voices"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), unique=True)
    tone: Mapped[str] = mapped_column(String(400), default="warm, professional, concise")
    sign_off: Mapped[str] = mapped_column(String(200), default="— The Team")
    language: Mapped[str] = mapped_column(String(16), default="auto")
    forbidden_phrases: Mapped[list] = mapped_column(JSON, default=list)
    talking_points: Mapped[list] = mapped_column(JSON, default=list)
    offer_compensation: Mapped[bool] = mapped_column(Boolean, default=False)
    max_words: Mapped[int] = mapped_column(Integer, default=90)

    organization: Mapped[Organization] = relationship(back_populates="brand_voice")


class ReplyDraft(Base):
    __tablename__ = "reply_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), unique=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[ReplyStatus] = mapped_column(
        Enum(ReplyStatus), default=ReplyStatus.pending_approval, index=True
    )
    model: Mapped[str] = mapped_column(String(64), default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    signal: Mapped[Signal] = relationship(back_populates="reply_draft")


# --- Benchmarks: the cross-tenant network effect ----------------------------

class BenchmarkStat(Base):
    """Anonymized aggregate per (industry, topic, period). No organization_id
    by design — raw tenant data never leaves the tenant. Published only when
    org_count >= the k-anonymity threshold."""

    __tablename__ = "benchmark_stats"
    __table_args__ = (
        UniqueConstraint("industry", "topic", "period", name="uq_benchmark_segment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    industry: Mapped[str] = mapped_column(String(80), index=True)
    topic: Mapped[str] = mapped_column(String(80), index=True)
    period: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    org_count: Mapped[int] = mapped_column(Integer)
    signal_count: Mapped[int] = mapped_column(Integer)
    avg_sentiment: Mapped[float] = mapped_column(Float)
    negative_share: Mapped[float] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --- Usage metering ----------------------------------------------------------

class UsageRecord(Base):
    """One row per enriched signal — the billable unit of the platform."""

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), default="signal_enriched")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
