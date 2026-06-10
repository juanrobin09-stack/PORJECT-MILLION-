"""The intelligence engine: enrichment, reply drafting, and synthesis.

Cost architecture:
- enrich   -> claude-haiku-4-5 on a cached system prompt (taxonomy included):
              the high-volume path, ~$0.001/signal.
- generate -> claude-opus-4-8: customer-facing writing and analytical
              synthesis, where quality IS the product.

All calls use structured outputs (`messages.parse`) against the contracts in
schemas.py. The engine is stateless and takes an injectable client so the
entire platform tests with zero network.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from sona.config import get_settings
from sona.core.taxonomy import normalize_topics
from sona.intelligence import prompts
from sona.intelligence.schemas import DraftedReply, SignalEnrichment, SynthesizedAnswer

logger = logging.getLogger("sona.intelligence")


class IntelligenceEngine:
    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self.settings = get_settings()
        self._client = client

    @property
    def client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        return self._client

    def enrich(self, signal: dict[str, Any]) -> tuple[SignalEnrichment, list[str]]:
        """Returns (enrichment with canonical topics, unmapped raw labels)."""
        response = self.client.messages.parse(
            model=self.settings.sona_model_enrich,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": prompts.ENRICH_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": prompts.render_signal(signal)}],
            output_format=SignalEnrichment,
        )
        enrichment = response.parsed_output
        # Defense in depth: taxonomy discipline is enforced in code, not only
        # in the prompt. Unmapped labels stay visible as raw_topics.
        canonical, unmapped = normalize_topics(enrichment.topics)
        enrichment.topics = canonical
        if unmapped:
            logger.debug("Unmapped topic labels (taxonomy candidates): %s", unmapped)
        return enrichment, unmapped

    def draft_reply(
        self, signal: dict[str, Any], enrichment: SignalEnrichment, voice: dict[str, Any]
    ) -> DraftedReply:
        user_content = "\n\n".join(
            [
                prompts.render_brand_voice(voice),
                prompts.render_signal(signal),
                f"ANALYSIS: sentiment={enrichment.sentiment.value} "
                f"(score {enrichment.sentiment_score:+.2f}), intent={enrichment.intent.value}, "
                f"risk={enrichment.risk_level.value}, topics={', '.join(enrichment.topics)}",
                "Write the public reply now.",
            ]
        )
        response = self.client.messages.parse(
            model=self.settings.sona_model_generate,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": prompts.REPLY_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
            output_format=DraftedReply,
        )
        return response.parsed_output

    def synthesize(self, question: str, signal_digest: str) -> SynthesizedAnswer:
        user_content = (
            f"QUESTION: {question}\n\nSIGNALS:\n{signal_digest}\n\nAnswer the question now."
        )
        response = self.client.messages.parse(
            model=self.settings.sona_model_generate,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=[
                {
                    "type": "text",
                    "text": prompts.SYNTHESIZE_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
            output_format=SynthesizedAnswer,
        )
        return response.parsed_output


_engine: IntelligenceEngine | None = None


def get_engine() -> IntelligenceEngine:
    global _engine
    if _engine is None:
        _engine = IntelligenceEngine()
    return _engine
