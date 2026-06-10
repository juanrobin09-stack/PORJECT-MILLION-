from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Plan, ResponseMode, ResponseStatus, RiskLevel, Sentiment


# --- Organizations ---

class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    plan: Plan = Plan.starter


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    plan: Plan
    api_key: str
    created_at: datetime


# --- Brand voice ---

class BrandVoiceUpsert(BaseModel):
    tone: str = "warm, professional, concise"
    sign_off: str = "— The Team"
    language: str = "auto"
    forbidden_phrases: list[str] = []
    talking_points: list[str] = []
    offer_compensation: bool = False
    max_words: int = Field(default=90, ge=20, le=300)


class BrandVoiceOut(BrandVoiceUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: int


# --- Locations ---

class LocationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    platform_ids: dict[str, str] = {}
    response_mode: ResponseMode = ResponseMode.approve


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    platform_ids: dict[str, str]
    response_mode: ResponseMode
    created_at: datetime


# --- Reviews ---

class ReviewIngest(BaseModel):
    location_id: int
    platform: str = "webhook"
    external_id: str
    author: str = "Anonymous"
    rating: int | None = Field(default=None, ge=1, le=5)
    text: str = ""
    review_created_at: datetime | None = None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_id: int
    platform: str
    external_id: str
    author: str
    rating: int | None
    text: str
    sentiment: Sentiment | None
    sentiment_score: float | None
    topics: list[str]
    risk_level: RiskLevel
    risk_reasons: list[str]
    churn_risk: bool
    ingested_at: datetime
    analyzed_at: datetime | None


# --- Responses ---

class ResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int
    text: str
    status: ResponseStatus
    model: str
    generated_at: datetime
    published_at: datetime | None


class ResponseEdit(BaseModel):
    text: str = Field(min_length=1)


# --- AI structured outputs (contract with the Claude engine) ---

class ReviewAnalysis(BaseModel):
    """Structured analysis Claude must return for every review."""

    sentiment: Sentiment
    sentiment_score: float = Field(ge=-1, le=1)
    topics: list[str] = Field(max_length=8, description="Short noun-phrase topics, e.g. 'wait time'")
    risk_level: RiskLevel
    risk_reasons: list[str] = Field(
        default=[],
        description="Why this review is risky: legal threat, health/safety claim, "
        "discrimination allegation, viral potential, fake-review suspicion",
    )
    churn_risk: bool = Field(description="True if the customer signals they won't return")
    summary: str = Field(description="One-sentence neutral summary of the review")


class DraftedResponse(BaseModel):
    """Structured response Claude must return when drafting a reply."""

    response_text: str = Field(description="The public reply, ready to publish")
    addresses_complaints: list[str] = Field(
        default=[], description="Which specific complaints the reply addresses"
    )
    escalate_to_human: bool = Field(
        description="True if a human should review before publishing regardless of mode"
    )
    escalation_reason: str = Field(default="")


class WeeklyInsights(BaseModel):
    """Structured weekly report Claude must return from a batch of reviews."""

    executive_summary: str
    top_strengths: list[str] = Field(max_length=5)
    top_issues: list[str] = Field(max_length=5)
    emerging_trends: list[str] = Field(max_length=5)
    recommended_actions: list[str] = Field(max_length=5)
    locations_at_risk: list[str] = Field(default=[], max_length=10)


# --- Insights / Alerts ---

class InsightReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_start: datetime
    period_end: datetime
    summary: str
    data: dict
    created_at: datetime


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int | None
    level: RiskLevel
    message: str
    delivered: bool
    created_at: datetime


class UsageOut(BaseModel):
    plan: Plan
    period: str
    responses_used: int
    responses_quota: int | None  # None = unlimited
