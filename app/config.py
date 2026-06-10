from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    resona_database_url: str = "sqlite:///./resona.db"
    resona_env: str = "development"

    # AI
    anthropic_api_key: str = ""
    resona_model_response: str = "claude-opus-4-8"
    resona_model_triage: str = "claude-haiku-4-5"
    resona_model_insights: str = "claude-opus-4-8"

    # Billing
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Connectors
    google_business_api_key: str = ""
    trustpilot_api_key: str = ""

    # Alerting
    resona_alert_webhook_url: str = ""

    # Worker cadence
    poll_interval_minutes: int = 15
    insights_weekday: int = 0  # Monday
    insights_hour_utc: int = 7

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
