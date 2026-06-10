from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    sona_database_url: str = "sqlite:///./sona.db"
    sona_env: str = "development"

    # AI
    anthropic_api_key: str = ""
    sona_model_enrich: str = "claude-haiku-4-5"     # high-volume structured triage
    sona_model_generate: str = "claude-opus-4-8"    # customer-facing writing + synthesis

    # Connectors (optional; the ingest API works without them)
    google_business_api_key: str = ""
    trustpilot_api_key: str = ""

    # Benchmarks — a segment is published only when at least this many
    # distinct organizations contribute to it (k-anonymity).
    sona_benchmark_min_orgs: int = 5

    # Worker cadence
    poll_interval_minutes: int = 15
    benchmark_hour_utc: int = 4

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
