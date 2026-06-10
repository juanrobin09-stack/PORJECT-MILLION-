import enum
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

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_api_key() -> str:
    return "rsn_" + secrets.token_urlsafe(32)


class Plan(str, enum.Enum):
    starter = "starter"      # $49/location/mo — 150 AI responses
    growth = "growth"        # $99/location/mo — 600 AI responses, insights
    scale = "scale"          # $249/location/mo — unlimited, alerts, API access


PLAN_RESPONSE_QUOTA: dict[Plan, int | None] = {
    Plan.starter: 150,
    Plan.growth: 600,
    Plan.scale: None,  # unlimited
}


class ResponseMode(str, enum.Enum):
    draft_only = "draft_only"          # AI drafts, human publishes elsewhere
    approve = "approve"                # AI drafts, human approves, Resona publishes
    auto_publish = "auto_publish"      # Resona publishes positive/neutral, queues risky


class ResponseStatus(str, enum.Enum):
    pending_approval = "pending_approval"
    approved = "approved"
    published = "published"
    rejected = "rejected"
    failed = "failed"


class Sentiment(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"
    mixed = "mixed"


class RiskLevel(str, enum.Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    plan: Mapped[Plan] = mapped_column(Enum(Plan), default=Plan.starter)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, default=new_api_key, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    locations: Mapped[list["Location"]] = relationship(back_populates="organization")
    brand_voice: Mapped["BrandVoice | None"] = relationship(
        back_populates="organization", uselist=False
    )


class BrandVoice(Base):
    """Per-organization voice profile that governs every AI-written response."""

    __tablename__ = "brand_voices"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), unique=True
    )
    tone: Mapped[str] = mapped_column(String(400), default="warm, professional, concise")
    sign_off: Mapped[str] = mapped_column(String(200), default="— The Team")
    language: Mapped[str] = mapped_column(String(16), default="auto")  # auto = mirror reviewer
    forbidden_phrases: Mapped[list] = mapped_column(JSON, default=list)
    talking_points: Mapped[list] = mapped_column(JSON, default=list)
    offer_compensation: Mapped[bool] = mapped_column(Boolean, default=False)
    max_words: Mapped[int] = mapped_column(Integer, default=90)

    organization: Mapped[Organization] = relationship(back_populates="brand_voice")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    platform_ids: Mapped[dict] = mapped_column(JSON, default=dict)  # {"google": "...", "trustpilot": "..."}
    response_mode: Mapped[ResponseMode] = mapped_column(
        Enum(ResponseMode), default=ResponseMode.approve
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped[Organization] = relationship(back_populates="locations")
    reviews: Mapped[list["Review"]] = relationship(back_populates="location")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("platform", "external_id", name="uq_platform_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), index=True)
    platform: Mapped[str] = mapped_column(String(40))  # google | trustpilot | webhook | ...
    external_id: Mapped[str] = mapped_column(String(120))
    author: Mapped[str] = mapped_column(String(200), default="Anonymous")
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5
    text: Mapped[str] = mapped_column(Text, default="")
    review_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # AI analysis (populated by the pipeline)
    sentiment: Mapped[Sentiment | None] = mapped_column(Enum(Sentiment), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1..1
    topics: Mapped[list] = mapped_column(JSON, default=list)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.none)
    risk_reasons: Mapped[list] = mapped_column(JSON, default=list)
    churn_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    location: Mapped[Location] = relationship(back_populates="reviews")
    response: Mapped["ReviewResponse | None"] = relationship(
        back_populates="review", uselist=False
    )


class ReviewResponse(Base):
    __tablename__ = "review_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"), unique=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[ResponseStatus] = mapped_column(
        Enum(ResponseStatus), default=ResponseStatus.pending_approval, index=True
    )
    model: Mapped[str] = mapped_column(String(64), default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    review: Mapped[Review] = relationship(back_populates="response")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    review_id: Mapped[int | None] = mapped_column(ForeignKey("reviews.id"), nullable=True)
    level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel))
    message: Mapped[str] = mapped_column(Text)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InsightReport(Base):
    __tablename__ = "insight_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSON, default=dict)  # structured insight payload
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UsageRecord(Base):
    """One row per billable AI response, for quota enforcement and Stripe metering."""

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40), default="ai_response")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
