"""Connector contract.

A connector pulls reviews from one platform for one location. Connectors are
stateless; the worker handles scheduling and dedup happens at the DB layer via
the (platform, external_id) unique constraint.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RawReview:
    external_id: str
    author: str = "Anonymous"
    rating: int | None = None
    text: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ReviewConnector(abc.ABC):
    """Subclass per platform. `platform` must match Location.platform_ids keys."""

    platform: str

    @abc.abstractmethod
    def is_configured(self) -> bool:
        """True when the required API credentials are present."""

    @abc.abstractmethod
    def fetch_reviews(self, platform_location_id: str, since: datetime | None = None) -> list[RawReview]:
        """Fetch reviews for one location, newest first."""
