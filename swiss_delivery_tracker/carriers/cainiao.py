"""Cainiao / AliExpress carrier - direct API."""

import json
import urllib.request
from datetime import datetime, timezone

from . import BASE_HEADERS


STATUS_MAP = {
    "WAIT_SELLER_SEND_GOODS": "pending",
    "SELLER_SEND_GOODS": "pending",
    "WAIT_BUYER_ACCEPT_GOODS": "in_transit",
    "DELIVERING": "in_transit",
    "SIGN": "delivered",
    "FAILED": "exception",
    "RETURNED": "exception",
}


def fetch(tracking_number):
    """Track a Cainiao/AliExpress parcel."""
    url = f"https://global.cainiao.com/global/detail.json?mailNos={tracking_number}&lang=en-US"
    req = urllib.request.Request(url, headers={
        **BASE_HEADERS,
        "Referer": "https://www.aliexpress.com/",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read().decode())

    module = (data.get("module") or data.get("data") or [{}])[0]
    raw_status = module.get("status", "")
    status = STATUS_MAP.get(raw_status, "in_transit" if raw_status else "unknown")

    latest = module.get("latestTrace") or module.get("globalCombinedLogisticsTraceDTO") or {}
    events_raw = module.get("detailList") or []
    events = [
        {
            "time": e.get("timeStr", ""),
            "location": "",
            "description": e.get("standerdDesc") or e.get("desc", ""),
        }
        for e in events_raw[:20]
    ]

    eta = module.get("globalEtaInfo") or {}
    expected = None
    if eta.get("deliveryMaxTime"):
        expected = datetime.fromtimestamp(
            eta["deliveryMaxTime"] / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d")

    return {
        "status": status,
        "last_status_text": latest.get("standerdDesc") or latest.get("desc") or raw_status,
        "last_update": latest.get("timeStr"),
        "expected_delivery": expected,
        "events": events,
    }
