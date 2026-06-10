from app.connectors.base import ReviewConnector, RawReview
from app.connectors.google import GoogleBusinessConnector
from app.connectors.trustpilot import TrustpilotConnector

ALL_CONNECTORS: list[type[ReviewConnector]] = [
    GoogleBusinessConnector,
    TrustpilotConnector,
]

__all__ = ["ReviewConnector", "RawReview", "ALL_CONNECTORS"]
