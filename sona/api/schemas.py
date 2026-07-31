from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from sona.models import (
    Intent,
    Plan,
    ReplyStatus,
    RiskLevel,
    Sentiment,
    SignalKind,
    Urgency,
)


# --- Organizations ---

class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    industry: str = Field(default="general", max_length=80)
    plan: Plan = Plan.developer


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    industry: str
    plan: Plan
    created_at: datetime


class OrganizationCreated(OrganizationOut):
    api_key: str  # returned exactly once — only the hash is stored


class UsageOut(BaseModel):
    plan: Plan
    period: str
    signals_enriched: int
    signal_quota: int | None


# --- Sources ---

class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: str = "api"
    config: dict = {}


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: str
    config: dict
    created_at: datetime


# --- Signals ---

class SignalIngest(BaseModel):
    source_id: int
    external_id: str = Field(min_length=1, max_length=160)
    kind: SignalKind = SignalKind.custom
    author: dict = {}
    content: str = ""
    rating: int | None = Field(default=None, ge=1, le=5)
    nps_score: int | None = Field(default=None, ge=0, le=10)
    meta: dict = {}
    occurred_at: datetime | None = None


class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    external_id: str
    kind: SignalKind
    author: dict
    content: str
    rating: int | None
    nps_score: int | None
    meta: dict
    occurred_at: datetime
    ingested_at: datetime
    sentiment: Sentiment | None
    sentiment_score: float | None
    language: str | None
    intent: Intent | None
    urgency: Urgency | None
    risk_level: RiskLevel
    risk_reasons: list
    churn_risk: bool
    topics: list
    raw_topics: list
    summary: str
    enriched_at: datetime | None


# --- Ask (natural-language synthesis) ---

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    kind: SignalKind | None = None
    days: int = Field(default=30, ge=1, le=365)
    max_signals: int = Field(default=200, ge=10, le=500)


class AskResponse(BaseModel):
    answer: str
    evidence_signal_ids: list[int]
    confidence: str
    caveats: str
    signals_considered: int


# --- Automations ---

class AutomationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    enabled: bool = True
    conditions: list[dict] = []
    action_type: str = Field(pattern="^(webhook|alert|draft_reply|tag)$")
    action_config: dict = {}


class AutomationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    enabled: bool
    conditions: list
    action_type: str
    action_config: dict
    created_at: datetime


class ActionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    automation_id: int | None
    signal_id: int
    action_type: str
    status: str
    detail: str
    created_at: datetime


# --- Benchmarks ---

class BenchmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    industry: str
    topic: str
    period: str
    org_count: int
    signal_count: int
    avg_sentiment: float
    negative_share: float


# --- Reputation module ---

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


class ReplyDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    signal_id: int
    text: str
    status: ReplyStatus
    model: str
    generated_at: datetime
    published_at: datetime | None


class ReplyDraftEdit(BaseModel):
    text: str = Field(min_length=1)
