"""SunYou carrier - JSONP API via sypost.net."""

import json
import re
import urllib.request
from datetime import datetime

from . import BASE_HEADERS


# displayStatus: "1"=in transit, "2"=arrived, "3"=pick up,
# "4"=undelivered, "5"=delivered, "6"=alert, "7"=expired
DISPLAY_STATUS_MAP = {
    "1": "in_transit",
    "2": "in_transit",
    "3": "out_for_delivery",
    "4": "exception",
    "5": "delivered",
    "6": "exception",
    "7": "exception",
}


def fetch(tracking_number):
    """Track a SunYou parcel via sypost.net JSONP API."""
    timestamp = f"{int(datetime.now().timestamp() * 1000)}-{hash(tracking_number) % 90000 + 10000}"
    url = f"https://sypost.net/queryTrack?queryTime={timestamp}&toLanguage=en_US&trackNumber={tracking_number}"
    req = urllib.request.Request(url, headers={**BASE_HEADERS, "Referer": "https://sypost.net/search"})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read().decode("utf-8", errors="replace")

    # Strip JSONP wrapper: searchCallback({...})
    match = re.match(r'^\s*\w+\((.*)\)\s*;?\s*$', raw, re.DOTALL)
    if not match:
        return {
            "status": "unknown",
            "last_status_text": "Invalid JSONP response",
            "last_update": None,
            "expected_delivery": None,
            "events": [],
        }

    data = json.loads(match.group(1))
    items = data.get("data") or []
    if not items or not items[0].get("has"):
        return {
            "status": "unknown",
            "last_status_text": "Not yet in system",
            "last_update": None,
            "expected_delivery": None,
            "events": [],
        }

    item = items[0]

    # Events from result.origin.items[] and result.destination.items[]
    all_events_raw = []
    result = item.get("result") or {}
    for section in ("origin", "destination"):
        section_data = result.get(section) or {}
        all_events_raw.extend(section_data.get("items") or [])

    all_events_raw.sort(key=lambda e: e.get("createTime", ""), reverse=True)

    events = [
        {
            "time": e.get("createTime", ""),
            "location": "",
            "description": e.get("content", ""),
        }
        for e in all_events_raw[:20]
    ]

    display_status = str(item.get("displayStatus", ""))
    status = DISPLAY_STATUS_MAP.get(display_status, "in_transit")
    last_content = item.get("lastContent", "")

    return {
        "status": status,
        "last_status_text": last_content or (events[0]["description"] if events else ""),
        "last_update": item.get("lastUpdate") or (events[0]["time"] if events else None),
        "expected_delivery": None,
        "events": events,
    }
