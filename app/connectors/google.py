"""Google Business Profile connector.

Uses the My Business API reviews endpoint:
GET https://mybusiness.googleapis.com/v4/{location_name}/reviews

Production setup requires an OAuth-verified GBP API project; the connector
degrades to inactive when no key is configured, in which case ingestion happens
via the /v1/reviews/ingest webhook instead.
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from app.config import get_settings
from app.connectors.base import RawReview, ReviewConnector

logger = logging.getLogger("resona.connectors.google")

STAR_MAP = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


class GoogleBusinessConnector(ReviewConnector):
    platform = "google"
    BASE_URL = "https://mybusiness.googleapis.com/v4"

    def __init__(self) -> None:
        self.api_key = get_settings().google_business_api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def fetch_reviews(self, platform_location_id: str, since: datetime | None = None) -> list[RawReview]:
        if not self.is_configured():
            return []
        resp = httpx.get(
            f"{self.BASE_URL}/{platform_location_id}/reviews",
            headers={"Authorization": f"Bearer {self.api_key}"},
            params={"pageSize": 50, "orderBy": "updateTime desc"},
            timeout=20.0,
        )
        resp.raise_for_status()
        out: list[RawReview] = []
        for item in resp.json().get("reviews", []):
            created = datetime.fromisoformat(item["createTime"].replace("Z", "+00:00"))
            if since is not None and created <= since:
                continue
            out.append(
                RawReview(
                    external_id=item["reviewId"],
                    author=item.get("reviewer", {}).get("displayName", "Anonymous"),
                    rating=STAR_MAP.get(item.get("starRating", ""), None),
                    text=item.get("comment", ""),
                    created_at=created,
                )
            )
        return out
