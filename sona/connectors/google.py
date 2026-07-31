"""Google Business Profile connector (reviews -> signals).

GET https://mybusiness.googleapis.com/v4/{location_name}/reviews
Source.config: {"location_name": "accounts/{aid}/locations/{lid}"}
"""

from __future__ import annotations

from datetime import datetime

import httpx

from sona.config import get_settings
from sona.connectors.base import RawSignal, SignalConnector
from sona.models import SignalKind

STAR_MAP = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


class GoogleBusinessConnector(SignalConnector):
    source_kind = "google"
    BASE_URL = "https://mybusiness.googleapis.com/v4"

    def __init__(self) -> None:
        self.api_key = get_settings().google_business_api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def fetch(self, source_config: dict, since: datetime | None = None) -> list[RawSignal]:
        location_name = source_config.get("location_name")
        if not self.is_configured() or not location_name:
            return []
        resp = httpx.get(
            f"{self.BASE_URL}/{location_name}/reviews",
            headers={"Authorization": f"Bearer {self.api_key}"},
            params={"pageSize": 50, "orderBy": "updateTime desc"},
            timeout=20.0,
        )
        resp.raise_for_status()
        out: list[RawSignal] = []
        for item in resp.json().get("reviews", []):
            created = datetime.fromisoformat(item["createTime"].replace("Z", "+00:00"))
            if since is not None and created <= since:
                continue
            out.append(
                RawSignal(
                    external_id=item["reviewId"],
                    kind=SignalKind.review,
                    author={"name": item.get("reviewer", {}).get("displayName", "Anonymous")},
                    rating=STAR_MAP.get(item.get("starRating", ""), None),
                    content=item.get("comment", ""),
                    occurred_at=created,
                )
            )
        return out
