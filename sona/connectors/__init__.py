from sona.connectors.base import RawSignal, SignalConnector
from sona.connectors.google import GoogleBusinessConnector
from sona.connectors.trustpilot import TrustpilotConnector

ALL_CONNECTORS: list[type[SignalConnector]] = [
    GoogleBusinessConnector,
    TrustpilotConnector,
]

__all__ = ["SignalConnector", "RawSignal", "ALL_CONNECTORS"]
