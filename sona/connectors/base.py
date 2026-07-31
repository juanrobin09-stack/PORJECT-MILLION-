"""Connector SDK.

A connector pulls signals from one external platform for one Source. Adding a
channel to Sona = implementing this interface; the canonical schema, pipeline,
automations, and benchmarks come for free. Dedup happens at the DB layer via
the (source_id, external_id) unique constraint.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sona.models import SignalKind


@dataclass
class RawSignal:
    external_id: str
    kind: SignalKind = SignalKind.custom
    author: dict = field(default_factory=dict)
    content: str = ""
    rating: int | None = None
    nps_score: int | None = None
    meta: dict = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SignalConnector(abc.ABC):
    """Subclass per platform. `source_kind` matches Source.kind."""

    source_kind: str

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """True when required API credentials are present."""

    @abc.abstractmethod
    def fetch(self, source_config: dict, since: datetime | None = None) -> list[RawSignal]:
        """Fetch signals for one source, newest first."""
