"""Spring GDS carrier - via PostNL International tracking API."""

import json
import urllib.request

from . import BASE_HEADERS


STATUS_MAP = {
    "Preparing": "pending",
    "In transit": "in_transit",
    "Transit": "in_transit",
    "Out for delivery": "out_for_delivery",
    "Delivered": "delivered",
    "Returned": "exception",
    "Exception": "exception",
}


def fetch(tracking_number):
    """Track a Spring GDS parcel via PostNL International (postnl.post).

    Uses an anonymous visitor token, no API key required.
    """
    # Step 1: Get anonymous visitor token
    token_body = json.dumps({}).encode()
    token_req = urllib.request.Request(
        "https://postnl.post/api/v1/auth/token",
        data=token_body,
        headers={
            **BASE_HEADERS,
            "Content-Type": "application/json",
            "Origin": "https://postnl.post",
            "Referer": "https://postnl.post/",
        },
    )
    with urllib.request.urlopen(token_req, timeout=10) as r:
        token_data = json.loads(r.read().decode())
    access_token = token_data["access_token"]

    # Step 2: Query tracking items
    track_body = json.dumps({"items": [tracking_number], "language_code": "en"}).encode()
    track_req = urllib.request.Request(
        "https://postnl.post/api/v1/tracking-items",
        data=track_body,
        headers={
            **BASE_HEADERS,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Origin": "https://postnl.post",
            "Referer": "https://postnl.post/",
        },
    )
    with urllib.request.urlopen(track_req, timeout=15) as r:
        resp = json.loads(r.read().decode())

    items = (resp.get("data") or {}).get("items") or []
    if not items:
        return {
            "status": "unknown",
            "last_status_text": "",
            "last_update": None,
            "expected_delivery": None,
            "events": [],
        }

    item = items[0]
    raw_events = item.get("events") or []

    events = [
        {
            "time": e.get("datetime_local", ""),
            "location": e.get("country_name") or e.get("country_code") or "",
            "description": e.get("status_description") or e.get("category") or "",
        }
        for e in raw_events
    ]

    status = "unknown"
    last_status_text = ""
    if raw_events:
        latest = raw_events[0]
        category = latest.get("category", "")
        status = STATUS_MAP.get(category, "in_transit" if category else "unknown")
        last_status_text = latest.get("status_description") or category

    return {
        "status": status,
        "last_status_text": last_status_text,
        "last_update": events[0]["time"] if events else None,
        "expected_delivery": None,
        "events": events,
    }
