"""UPS carrier - CDP (Chrome DevTools Protocol) scraper.

⚠️ EXPERIMENTAL: This carrier uses browser automation via Chrome DevTools
Protocol to scrape the UPS tracking page. It requires a running Chrome/Chromium
instance with remote debugging enabled.

Requirements:
    - Chrome/Chromium running with: --remote-debugging-port=<port> --remote-allow-origins=*
    - Python websocket-client package: pip install websocket-client

Why CDP instead of API:
    UPS's official tracking API requires OAuth2 credentials and a developer
    account. The web scraper approach works without any credentials but is
    slower (~20s per lookup) and fragile if UPS changes their frontend.

Usage:
    The CDP port defaults to 18800. Override with the UPS_CDP_PORT env var
    or pass cdp_port to fetch().
"""

import json
import os
import re
import sys
import time
import http.client

try:
    import websocket
except ImportError:
    websocket = None


DEFAULT_CDP_PORT = 18800


def fetch(tracking_number, tracking_url=None, cdp_port=None):
    """Track a UPS parcel by scraping ups.com via CDP.

    Args:
        tracking_number: UPS tracking number (e.g. 1Z...)
        tracking_url: Ignored (kept for interface consistency)
        cdp_port: Chrome DevTools Protocol port (default: 18800 or UPS_CDP_PORT env)

    Returns:
        dict with status, last_status_text, last_update, expected_delivery, events
    """
    if websocket is None:
        return {
            "status": "unknown",
            "last_status_text": "websocket-client not installed (pip install websocket-client)",
            "last_update": None,
            "expected_delivery": None,
            "events": [],
        }

    port = cdp_port or int(os.environ.get("UPS_CDP_PORT", DEFAULT_CDP_PORT))

    try:
        conn = http.client.HTTPConnection("localhost", port, timeout=10)
        conn.request("PUT", "/json/new?https://www.ups.com/track?loc=en_US")
        tab = json.loads(conn.getresponse().read())
    except (ConnectionRefusedError, OSError):
        return {
            "status": "unknown",
            "last_status_text": f"Chrome not running on CDP port {port}",
            "last_update": None,
            "expected_delivery": None,
            "events": [],
        }

    ws_url = tab["webSocketDebuggerUrl"]
    tab_id = tab["id"]

    try:
        time.sleep(6)
        sock = websocket.create_connection(ws_url, timeout=30)

        # Dismiss cookie/consent banners
        sock.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": (
                    "document.querySelectorAll('button').forEach(b => {"
                    " if (b.textContent.includes('Essential') || b.textContent.trim()==='\\u00d7')"
                    " b.click(); }); 'ok'"
                ),
                "returnByValue": True,
            },
        }))
        sock.recv()
        time.sleep(2)

        # Fill tracking number using React-compatible setter
        fill_js = f"""
        const ta = document.querySelector('textarea');
        if (ta) {{
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            ).set;
            setter.call(ta, '{tracking_number}');
            ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
            ta.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
        'filled'
        """
        sock.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {"expression": fill_js, "returnByValue": True},
        }))
        sock.recv()
        time.sleep(1)

        # Click Track button
        sock.send(json.dumps({
            "id": 3,
            "method": "Runtime.evaluate",
            "params": {
                "expression": (
                    "var btns = document.querySelectorAll('button');"
                    " for (var b of btns) {"
                    " if (b.textContent.trim()==='Track') { b.click(); break; } }"
                    " 'clicked'"
                ),
                "returnByValue": True,
            },
        }))
        sock.recv()

        # Wait for results to load
        time.sleep(12)

        # Extract tracking data from page
        extract_js = """
        (() => {
            const app = document.querySelector('app-root');
            if (!app) return JSON.stringify({error: 'page not loaded'});
            const text = app.textContent.replace(/\\s+/g, ' ');

            if (text.includes('not valid tracking numbers'))
                return JSON.stringify({error: 'invalid'});
            if (text.includes('Enter up to 25') && !text.includes('Your shipment'))
                return JSON.stringify({error: 'no results'});

            let status = 'unknown';
            if (text.includes('Delivered')) status = 'delivered';
            else if (/Out (f|F)or Delivery/.test(text)) status = 'out_for_delivery';
            else if (text.includes('On the Way') || text.includes('In Transit')
                     || text.includes('We Have Your Package')) status = 'in_transit';
            else if (text.includes('Label Created') || text.includes('Shipment Ready'))
                status = 'pending';

            let last_event = '';
            const m = text.match(/Current Event\\s+(.+?)\\s+Future Event/);
            if (m) last_event = m[1].trim();

            let eta = '';
            const em = text.match(/Estimated delivery\\s+(.+?)\\s+Tracking Status/);
            if (em) eta = em[1].trim();

            let ship_to = '';
            const sm = text.match(/Ship To\\s+(.+?)\\s+(?:Past|Current)/);
            if (sm) ship_to = sm[1].trim();

            return JSON.stringify({status, last_event, eta, ship_to});
        })()
        """

        sock.send(json.dumps({
            "id": 4,
            "method": "Runtime.evaluate",
            "params": {"expression": extract_js, "returnByValue": True, "awaitPromise": False},
        }))
        resp = json.loads(sock.recv())
        sock.close()

        result_val = resp.get("result", {}).get("result", {}).get("value", "")
        if not result_val:
            return {
                "status": "unknown",
                "last_status_text": "Could not extract tracking data",
                "last_update": None,
                "expected_delivery": None,
                "events": [],
            }

        parsed = json.loads(result_val)
        if "error" in parsed:
            return {
                "status": "unknown",
                "last_status_text": parsed["error"],
                "last_update": None,
                "expected_delivery": None,
                "events": [],
            }

        events = []
        if parsed.get("last_event"):
            events.append({
                "time": "",
                "location": parsed.get("ship_to", ""),
                "description": parsed["last_event"],
            })

        return {
            "status": parsed.get("status", "unknown"),
            "last_status_text": parsed.get("last_event", ""),
            "last_update": None,
            "expected_delivery": parsed.get("eta") or None,
            "events": events,
        }
    finally:
        # Clean up: close the tab
        try:
            conn2 = http.client.HTTPConnection("localhost", port, timeout=5)
            conn2.request("GET", f"/json/close/{tab_id}")
            conn2.getresponse()
        except Exception:
            pass
