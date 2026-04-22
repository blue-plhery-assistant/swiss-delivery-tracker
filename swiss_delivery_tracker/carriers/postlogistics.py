"""PostLogistics carrier - direct API (eosapi), no key needed.

Note: This is NOT 17track. PostLogistics has its own public tracking API
at https://eosapi.postlogistics.ch.
"""

import json
import urllib.request

from . import BASE_HEADERS


def fetch(tracking_number):
    """Track a PostLogistics parcel via their public API."""
    url = "https://eosapi.postlogistics.ch/api/trackandtrace/public?culture=fr-FR"
    payload = json.dumps({"Identifier": tracking_number}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={
        **BASE_HEADERS,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://tracking.postlogistics.ch",
        "Referer": "https://tracking.postlogistics.ch/",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8"))

    items = data.get("Data", [])
    if not items:
        return {
            "status": "unknown",
            "last_status_text": "No data",
            "last_update": None,
            "expected_delivery": None,
            "events": [],
        }

    item = items[0]
    history = item.get("History", [])
    drive = item.get("DriveAndArrive")

    events = []
    for h in history:
        events.append({
            "time": h.get("TimeStamp", ""),
            "location": h.get("City", ""),
            "description": h.get("Description", ""),
        })
    events.sort(key=lambda e: e.get("time", ""), reverse=True)

    latest = history[-1] if history else {}
    latest_status = latest.get("Status", "")
    latest_desc = latest.get("Description", "")

    status = "in_transit"
    if latest_status in ("DEL", "DLV", "POD", "SIG"):
        status = "delivered"
    elif latest_status == "NTF":
        status = "pending"

    expected_delivery = None
    if drive:
        eta = drive.get("PlannedDeliveryDate") or drive.get("EstimatedArrival")
        if eta:
            expected_delivery = eta[:10] if len(eta) >= 10 else eta

    return {
        "status": status,
        "last_status_text": latest_desc or latest_status,
        "last_update": latest.get("TimeStamp"),
        "expected_delivery": expected_delivery,
        "events": events,
    }
