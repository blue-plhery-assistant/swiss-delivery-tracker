"""Core tracking logic - load/save deliveries and dispatch to carriers."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .carriers import swiss_post, quickpac, cainiao, sunyou, planzer, hermes, spring_gds, postlogistics, dachser
from .models import normalize_carrier

DEFAULT_DATA_DIR = Path.home() / ".swiss-delivery-tracker"
DEFAULT_DATA_FILE = DEFAULT_DATA_DIR / "deliveries.json"

# Map carrier names to their fetch modules
CARRIER_MODULES = {
    "Swiss Post": swiss_post,
    "Quickpac": quickpac,
    "AliExpress": cainiao,
    "SunYou": sunyou,
    "Planzer": planzer,
    "Hermes Einrichtungs-Service": hermes,
    "Spring GDS": spring_gds,
    "PostLogistics": postlogistics,
    "Dachser": dachser,
}


def load_deliveries(data_file=None):
    """Load deliveries from JSON file."""
    path = Path(data_file) if data_file else DEFAULT_DATA_FILE
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def save_deliveries(deliveries, data_file=None):
    """Save deliveries to JSON file."""
    path = Path(data_file) if data_file else DEFAULT_DATA_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(deliveries, f, indent=2, ensure_ascii=False)


def next_id(deliveries):
    """Generate the next delivery ID."""
    max_id = max((int(d["id"]) for d in deliveries if str(d.get("id", "")).isdigit()), default=0)
    return str(max_id + 1)


def add_delivery(deliveries, tracking_number, carrier, description, source=None, origin=None, notes=None):
    """Add a new delivery and return the entry."""
    carrier = normalize_carrier(carrier)
    now = datetime.now(tz=timezone.utc).astimezone().isoformat()

    entry = {
        "id": next_id(deliveries),
        "tracking_number": tracking_number,
        "carrier": carrier,
        "description": description,
        "source": source or carrier,
        "status": "pending" if not tracking_number else "in_transit",
        "last_status_text": "",
        "last_update": None,
        "expected_delivery": None,
        "origin": origin,
        "destination": "CH",
        "events": [],
        "added_at": now,
    }
    if notes:
        entry["notes"] = notes

    deliveries.append(entry)
    return entry


def update_delivery(delivery):
    """Fetch fresh tracking data for a single delivery. Returns True if updated."""
    carrier = delivery.get("carrier", "")
    tracking = delivery.get("tracking_number")

    if not tracking:
        return False

    module = CARRIER_MODULES.get(carrier)
    if not module:
        print(f"  No tracker for carrier '{carrier}', skipping {tracking}", file=sys.stderr)
        return False

    try:
        if carrier == "Dachser":
            result = module.fetch(tracking, delivery.get("tracking_url"))
        else:
            result = module.fetch(tracking)
        delivery.update(result)
        return True
    except Exception as e:
        print(f"  Error tracking {tracking} ({carrier}): {e}", file=sys.stderr)
        return False


def update_all(deliveries, include_delivered=False):
    """Update all active deliveries. Returns (updated, errors) counts."""
    updated = 0
    errors = 0

    active = [
        d for d in deliveries
        if d.get("status") not in ("delivered", "removed") or include_delivered
    ]

    for d in active:
        carrier = d.get("carrier", "")
        tracking = d.get("tracking_number", "?")
        print(f"Updating {tracking} ({carrier})...", end=" ", flush=True)

        if update_delivery(d):
            print(f"{d.get('status', '?')} - {d.get('last_status_text', '')}")
            updated += 1

            # Cross-check: Quickpac parcels may also have Planzer data
            if carrier == "Quickpac" and d.get("status") != "delivered":
                _planzer_crosscheck(d)
        else:
            print("skipped")
            errors += 1

    return updated, errors


def _planzer_crosscheck(delivery):
    """For Quickpac parcels, also check Planzer for ETA and cross-border events."""
    try:
        result = planzer.fetch(delivery["tracking_number"])
        # Merge ETA if Quickpac doesn't have one
        if result.get("expected_delivery") and not delivery.get("expected_delivery"):
            delivery["expected_delivery"] = result["expected_delivery"]
        # Merge cross-border events
        existing = {e.get("description", "") for e in (delivery.get("events") or [])}
        new_events = [e for e in (result.get("events") or []) if e.get("description") not in existing]
        if new_events:
            merged = (delivery.get("events") or []) + new_events
            merged.sort(key=lambda e: e.get("time", ""), reverse=True)
            delivery["events"] = merged
        # Upgrade status if Planzer shows more progress
        if delivery.get("status") in ("pending", "unknown") and result.get("status") == "in_transit":
            delivery["status"] = "in_transit"
            delivery["last_status_text"] = result["last_status_text"] + " (via Planzer)"
    except Exception:
        pass  # Planzer cross-check is best-effort


def remove_delivery(deliveries, tracking_number):
    """Mark a delivery as removed. Returns the delivery or None."""
    for d in deliveries:
        if d.get("tracking_number") == tracking_number or d.get("id") == tracking_number:
            d["status"] = "removed"
            return d
    return None
