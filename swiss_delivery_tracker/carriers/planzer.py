"""Planzer carrier - direct API, no auth needed."""

import json
import urllib.request

from . import BASE_HEADERS


STATUS_MAP = {
    "Recorded": "pending",
    "Transferred": "in_transit",
    "Shipment on the way": "in_transit",
    "In delivery": "out_for_delivery",
    "Shipment out for delivery": "out_for_delivery",
    "Delivered": "delivered",
    "Not delivered": "exception",
}


def shipment_number(tracking_number):
    """Extract the Planzer shipment number from an Ikea-style order number.

    E.g. '84693.0055089536' -> '55089536'. If already short, return as-is.
    """
    if "." in tracking_number:
        raw = tracking_number.split(".", 1)[1]
        return raw.lstrip("0") or raw
    return tracking_number


def fetch(tracking_number):
    """Track a Planzer parcel."""
    shipment_nr = shipment_number(tracking_number)
    url = f"https://api.tracking.app.planzer.ch/api/v1/shipments/{shipment_nr}/Pak"
    req = urllib.request.Request(url, headers={**BASE_HEADERS})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode())

    overall = data.get("overallStatus", {})
    status_text = overall.get("text", {}).get("english", "")
    status = STATUS_MAP.get(status_text, "in_transit" if status_text else "unknown")

    delivery_day = data.get("deliveryDay") or {}
    expected = delivery_day.get("date")

    positions = data.get("transportPositions") or []
    events = []
    for pos in positions:
        for evt in (pos.get("positionEvents") or []):
            events.append({
                "time": evt.get("createdAt", ""),
                "location": "",
                "description": evt.get("text", {}).get("english", ""),
            })
    events.sort(key=lambda e: e.get("time", ""), reverse=True)

    return {
        "status": status,
        "last_status_text": status_text,
        "last_update": events[0]["time"] if events else None,
        "expected_delivery": expected,
        "events": events,
    }
