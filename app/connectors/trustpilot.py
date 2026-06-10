"""Trustpilot connector.

Uses the Business Units API:
GET https://api.trustpilot.com/v1/business-units/{id}/reviews
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from app.config import get_settings
from app.connectors.base import RawReview, ReviewConnector

logger = logging.getLogger("resona.connectors.trustpilot")


class TrustpilotConnector(ReviewConnector):
    platform = "trustpilot"
    BASE_URL = "https://api.trustpilot.com/v1"

    def __init__(self) -> None:
        self.api_key = get_settings().trustpilot_api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def fetch_reviews(self, platform_location_id: str, since: datetime | None = None) -> list[RawReview]:
        if not self.is_configured():
            return []
        resp = httpx.get(
            f"{self.BASE_URL}/business-units/{platform_location_id}/reviews",
            params={"apikey": self.api_key, "perPage": 50, "orderBy": "createdat.desc"},
            timeout=20.0,
        )
        resp.raise_for_status()
        out: list[RawReview] = []
        for item in resp.json().get("reviews", []):
            created = datetime.fromisoformat(item["createdAt"].replace("Z", "+00:00"))
            if since is not None and created <= since:
                continue
            out.append(
                RawReview(
                    external_id=item["id"],
                    author=item.get("consumer", {}).get("displayName", "Anonymous"),
                    rating=item.get("stars"),
                    text=(item.get("title", "") + "\n" + item.get("text", "")).strip(),
                    created_at=created,
                )
            )
        return out
