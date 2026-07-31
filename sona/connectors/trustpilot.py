"""Trustpilot connector (reviews -> signals).

GET https://api.trustpilot.com/v1/business-units/{id}/reviews
Source.config: {"business_unit_id": "..."}
"""

from __future__ import annotations

from datetime import datetime

import httpx

from sona.config import get_settings
from sona.connectors.base import RawSignal, SignalConnector
from sona.models import SignalKind


class TrustpilotConnector(SignalConnector):
    source_kind = "trustpilot"
    BASE_URL = "https://api.trustpilot.com/v1"

    def __init__(self) -> None:
        self.api_key = get_settings().trustpilot_api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def fetch(self, source_config: dict, since: datetime | None = None) -> list[RawSignal]:
        unit_id = source_config.get("business_unit_id")
        if not self.is_configured() or not unit_id:
            return []
        resp = httpx.get(
            f"{self.BASE_URL}/business-units/{unit_id}/reviews",
            params={"apikey": self.api_key, "perPage": 50, "orderBy": "createdat.desc"},
            timeout=20.0,
        )
        resp.raise_for_status()
        out: list[RawSignal] = []
        for item in resp.json().get("reviews", []):
            created = datetime.fromisoformat(item["createdAt"].replace("Z", "+00:00"))
            if since is not None and created <= since:
                continue
            out.append(
                RawSignal(
                    external_id=item["id"],
                    kind=SignalKind.review,
                    author={"name": item.get("consumer", {}).get("displayName", "Anonymous")},
                    rating=item.get("stars"),
                    content=(item.get("title", "") + "\n" + item.get("text", "")).strip(),
                    occurred_at=created,
                )
            )
        return out
