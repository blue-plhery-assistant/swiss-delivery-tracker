"""Hermes Einrichtungs-Service (HES) carrier - direct API."""

import json
import urllib.request

from . import BASE_HEADERS


STATUS_MAP = {
    40: "pending",       # electronically announced
    10100: "pending",    # dispositionsfähig
    20000: "in_transit",
    30000: "out_for_delivery",
    40000: "delivered",
    50000: "exception",
}


def fetch(tracking_number):
    """Track a Hermes Einrichtungs-Service parcel."""
    url = f"https://myhes.de/api/request/auftragsdaten?parcelNumber={tracking_number}"
    req = urllib.request.Request(url, headers={**BASE_HEADERS})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode())

    body = data.get("body", data)
    auftrag = body.get("auftragsdaten", {})
    journey = auftrag.get("statusjourneyDto", {})

    # Combine both event lists, sorted by time desc
    all_events = (journey.get("auftragstatusdaten") or []) + (journey.get("statusdaten") or [])
    all_events.sort(key=lambda e: e.get("sendungsstatusBuchungszeitpunkt", ""), reverse=True)

    events = [
        {
            "time": e.get("sendungsstatusBuchungszeitpunkt", ""),
            "location": "",
            "description": e.get("sendungsstatus", ""),
        }
        for e in all_events
    ]

    # Status from latest event
    latest_id = all_events[0].get("sendungsstatusId", 0) if all_events else 0
    if latest_id >= 40000:
        status = "delivered"
    elif latest_id >= 30000:
        status = "out_for_delivery"
    elif latest_id >= 20000:
        status = "in_transit"
    else:
        status = STATUS_MAP.get(latest_id, "pending")

    lieferdatum = auftrag.get("lieferdatum") or auftrag.get("hesBasicLieferterminZeit")

    return {
        "status": status,
        "last_status_text": events[0]["description"] if events else "",
        "last_update": events[0]["time"] if events else None,
        "expected_delivery": lieferdatum,
        "events": events,
    }
