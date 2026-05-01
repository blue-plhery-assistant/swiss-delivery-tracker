"""Data models for deliveries."""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class TrackingEvent:
    time: str = ""
    location: str = ""
    description: str = ""


@dataclass
class TrackingResult:
    status: str = "unknown"
    last_status_text: str = ""
    last_update: Optional[str] = None
    expected_delivery: Optional[str] = None
    events: list = field(default_factory=list)

    def to_dict(self):
        return {
            "status": self.status,
            "last_status_text": self.last_status_text,
            "last_update": self.last_update,
            "expected_delivery": self.expected_delivery,
            "events": self.events,
        }


@dataclass
class Delivery:
    id: str = ""
    tracking_number: Optional[str] = None
    carrier: str = ""
    description: str = ""
    source: str = ""
    status: str = "pending"
    last_status_text: str = ""
    last_update: Optional[str] = None
    expected_delivery: Optional[str] = None
    origin: Optional[str] = None
    destination: str = "CH"
    events: list = field(default_factory=list)
    added_at: str = ""
    notes: Optional[str] = None
    # Extra fields for specific carriers
    tracking_url: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        # Remove None values for cleaner JSON
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "Delivery":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# Carrier name normalization
CARRIER_ALIASES = {
    "swiss post": "Swiss Post",
    "swisspost": "Swiss Post",
    "quickpac": "Quickpac",
    "quickpak": "Quickpac",
    "aliexpress": "AliExpress",
    "cainiao": "AliExpress",
    "hermes": "Hermes Einrichtungs-Service",
    "hes": "Hermes Einrichtungs-Service",
    "hermes einrichtungs-service": "Hermes Einrichtungs-Service",
    "planzer": "Planzer",
    "dachser": "Dachser",
    "spring gds": "Spring GDS",
    "spring": "Spring GDS",
    "postlogistics": "PostLogistics",
    "sunyou": "SunYou",
    "sun you": "SunYou",
    "ups": "UPS",
}


def normalize_carrier(name: str) -> str:
    return CARRIER_ALIASES.get(name.lower().strip(), name)
