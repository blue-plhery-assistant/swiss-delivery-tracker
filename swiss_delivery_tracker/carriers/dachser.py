"""Dachser carrier - public tracking page scraping.

Note: Dachser uses an Angular SPA for tracking. The public tracking URL
includes auth parameters, so you need the full URL (not just a tracking number).
Results may be limited since we can't fully render the JS SPA.
"""

import re
import urllib.request

from . import BASE_HEADERS


def fetch(tracking_number, tracking_url=None):
    """Track a Dachser parcel. Requires tracking_url with auth params.

    Since Dachser uses a JS SPA, parsing is best-effort from page source.
    """
    if not tracking_url:
        return {
            "status": "unknown",
            "last_status_text": "No tracking URL provided (Dachser requires full URL with auth params)",
            "last_update": None,
            "expected_delivery": None,
            "events": [],
        }

    req = urllib.request.Request(tracking_url, headers={**BASE_HEADERS})
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8", errors="replace")

    status = "in_transit"
    last_status = ""
    events = []

    status_match = re.search(r'"status"\s*:\s*"([^"]+)"', html)
    if status_match:
        raw = status_match.group(1).lower()
        if "deliver" in raw and "pending" not in raw:
            status = "delivered"
        last_status = status_match.group(1)

    return {
        "status": status,
        "last_status_text": last_status or "Check tracking URL",
        "last_update": None,
        "expected_delivery": None,
        "events": events,
    }
