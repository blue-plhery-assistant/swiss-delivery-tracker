"""Swiss Post carrier - 4-step flow with CSRF token."""

import json
import urllib.request
import urllib.parse

from . import BASE_HEADERS, make_opener


STATUS_MAP = {
    "TO_BE_DELIVERED": "in_transit",
    "DELIVERED": "delivered",
    "IN_DELIVERY": "out_for_delivery",
    "NOT_DELIVERED": "exception",
    "RETURNED": "exception",
    "CUSTOMS": "in_transit",
    "REGISTERED": "pending",
}


def fetch(tracking_number):
    """Track a Swiss Post parcel.

    Flow: /user -> /history (POST) -> /history/not-included/{hash} -> events
    """
    opener = make_opener()
    headers = {
        **BASE_HEADERS,
        "Referer": "https://service.post.ch/ekp-web/ui/",
    }
    BASE = "https://service.post.ch/ekp-web/api"

    # Step 1: get anonymous userId + CSRF token
    with opener.open(urllib.request.Request(f"{BASE}/user", headers=headers), timeout=10) as r:
        csrf = r.headers.get("x-csrf-token", "")
        user_data = json.loads(r.read().decode())
        user_id = user_data["userIdentifier"]
    headers["x-csrf-token"] = csrf

    # Step 2: POST search query -> get hash
    url2 = f"{BASE}/history?userId={urllib.parse.quote(user_id)}"
    body2 = json.dumps({"searchQuery": tracking_number}).encode()
    req2 = urllib.request.Request(url2, data=body2, headers={**headers, "Content-Type": "application/json"})
    with opener.open(req2, timeout=10) as r:
        hash_val = json.loads(r.read().decode())["hash"]

    # Step 3: get shipment details (includes events)
    url3 = f"{BASE}/history/not-included/{hash_val}?userId={urllib.parse.quote(user_id)}"
    with opener.open(urllib.request.Request(url3, headers=headers), timeout=10) as r:
        items = json.loads(r.read().decode())

    if not items:
        return {
            "status": "unknown",
            "last_status_text": "",
            "last_update": None,
            "expected_delivery": None,
            "events": [],
        }

    item = items[0]
    global_status = item.get("globalStatus", "")
    status = STATUS_MAP.get(global_status, "in_transit")

    raw_events = item.get("events") or []
    events = [
        {
            "time": e.get("timestamp", ""),
            "location": (e.get("city") or "") + (" " + e.get("zip", "") if e.get("zip") else ""),
            "description": e.get("description", "") or e.get("eventCode", ""),
        }
        for e in raw_events
    ]

    calc_delivery = item.get("calculatedDeliveryDate") or item.get("deliveryDate")
    delivery_range = item.get("deliveryRange")
    if not calc_delivery and delivery_range:
        calc_delivery = delivery_range.get("start") or delivery_range.get("end")
    last_event_dt = item.get("lastEventDateTime")

    return {
        "status": status,
        "last_status_text": global_status,
        "last_update": last_event_dt,
        "expected_delivery": calc_delivery,
        "events": events,
    }
