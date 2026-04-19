"""Quickpac carrier - direct API, no auth needed."""

import json
import urllib.request

from . import BASE_HEADERS


def fetch(tracking_number):
    """Track a Quickpac parcel."""
    url = f"https://parcelsearch.quickpac.ch/api/ParcelSearch/GetPublicTracking/{tracking_number}/"
    req = urllib.request.Request(url, headers={
        **BASE_HEADERS,
        "Origin": "https://quickpac.ch",
        "Referer": "https://quickpac.ch/en/tracking",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode())

    code = data.get("LastStatusCode", 0)
    # Status codes: 1xxx=pending/transit, 2000-2099=transit,
    # 2100+=deposited/delivered, 3xxx=delivered, 4xxx=exception
    if code >= 4000:
        status = "exception"
    elif code >= 3000:
        status = "delivered"
    elif code >= 2100:
        status = "delivered"  # 2100+ = deposited/delivered (e.g. 2104 = sicher deponiert)
    elif code >= 2000:
        status = "in_transit"
    elif code >= 1200:
        status = "in_transit"
    elif code >= 1000:
        status = "pending"
    else:
        status = "unknown"

    events = [
        {
            "time": e.get("Time", ""),
            "location": "",
            "description": e.get("StatusText", ""),
        }
        for e in (data.get("Protocol") or [])
    ]

    return {
        "status": status,
        "last_status_text": data.get("LastStatus", ""),
        "last_update": events[0]["time"] if events else None,
        "expected_delivery": None,
        "events": events,
    }
