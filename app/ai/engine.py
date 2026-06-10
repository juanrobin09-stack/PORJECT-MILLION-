"""Claude-powered analysis, response drafting, and insight generation.

Design notes:
- Structured outputs everywhere: `client.messages.parse()` with Pydantic models
  guarantees valid, schema-conformant payloads (no JSON repair code paths).
- Prompt caching: system prompts are static module-level strings marked with
  `cache_control`, so the per-review marginal cost is the review text only.
- Model tiers (configurable via env):
    * triage/analysis  -> claude-haiku-4-5   (high volume, low cost)
    * response writing -> claude-opus-4-8    (the product IS the writing quality)
    * weekly insights  -> claude-opus-4-8 with adaptive thinking (hard reasoning)
- The engine is a thin, stateless class so tests can inject a fake client.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from app.ai import prompts
from app.config import get_settings
from app.schemas import DraftedResponse, ReviewAnalysis, WeeklyInsights

logger = logging.getLogger("resona.ai")


class AIEngine:
    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self.settings = get_settings()
        self._client = client

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    # --- Review analysis (sentiment, topics, risk) ---

    def analyze_review(self, review: dict[str, Any]) -> ReviewAnalysis:
        response = self.client.messages.parse(
            model=self.settings.resona_model_triage,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": prompts.ANALYSIS_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompts.render_review(review)}],
            output_format=ReviewAnalysis,
        )
        return response.parsed_output

    # --- Response drafting ---

    def draft_response(
        self, review: dict[str, Any], analysis: ReviewAnalysis, voice: dict[str, Any]
    ) -> DraftedResponse:
        user_content = "\n\n".join(
            [
                prompts.render_brand_voice(voice),
                prompts.render_review(review),
                f"ANALYSIS: sentiment={analysis.sentiment.value} "
                f"(score {analysis.sentiment_score:+.2f}), "
                f"risk={analysis.risk_level.value}, topics={', '.join(analysis.topics)}",
                "Write the public reply now.",
            ]
        )
        response = self.client.messages.parse(
            model=self.settings.resona_model_response,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": prompts.RESPONSE_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
            output_format=DraftedResponse,
        )
        return response.parsed_output

    # --- Weekly insights ---

    def weekly_insights(
        self, review_digest: str, baseline_summary: str = ""
    ) -> WeeklyInsights:
        """review_digest: pre-aggregated, compact text rendering of the week's
        analyzed reviews (built by insight_service to control token spend)."""
        user_content = (
            (f"BASELINE (last report): {baseline_summary}\n\n" if baseline_summary else "")
            + "THIS WEEK'S ANALYZED REVIEWS:\n"
            + review_digest
            + "\n\nProduce the weekly report now."
        )
        response = self.client.messages.parse(
            model=self.settings.resona_model_insights,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=[
                {
                    "type": "text",
                    "text": prompts.INSIGHTS_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
            output_format=WeeklyInsights,
        )
        return response.parsed_output


_engine: AIEngine | None = None


def get_engine() -> AIEngine:
    global _engine
    if _engine is None:
        _engine = AIEngine()
    return _engine
