"""Dachser carrier - JSON API (no browser needed).

Dachser Iberia exposes a JSON API at /api/utilidades/seguimiento-publico/detalle.
The public tracking URL includes a hash parameter for auth.
We convert the SPA URL to the API URL to get structured JSON data.
"""

import json
import urllib.request

from . import BASE_HEADERS


def fetch(tracking_number, tracking_url=None):
    """Track a Dachser parcel via their JSON API.

    Requires tracking_url with hash param (e.g. from Dachser email notifications).
    """
    if not tracking_url:
        return {
            "status": "unknown",
            "last_status_text": "No tracking URL provided (Dachser requires full URL with hash)",
            "last_update": None,
            "expected_delivery": None,
            "events": [],
        }

    # Convert SPA URL to API URL
    # SPA: .../customerarea/utilidades/seguimiento-publico/detalle?hash=...
    # API: .../api/utilidades/seguimiento-publico/detalle?hash=...
    api_url = tracking_url.replace("/customerarea/utilidades/", "/api/utilidades/")

    req = urllib.request.Request(api_url, headers={
        **BASE_HEADERS,
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8"))

    # Map status
    estado_text = data.get("estadoExpedicion", "")
    cod_estado = data.get("codEstado", 0)
    status = "in_transit"
    estado_lower = estado_text.lower()
    if "entregad" in estado_lower or "delivered" in estado_lower:
        status = "delivered"
    elif "pendiente" in estado_lower or "pending" in estado_lower:
        status = "in_transit"
    elif cod_estado >= 200:
        status = "delivered"

    # Parse events from incidenciaExpedicionData
    events = []
    for inc in data.get("incidenciaExpedicionData", []):
        events.append({
            "time": inc.get("fechaIncidencia", ""),
            "location": inc.get("delegacion", "") or "",
            "description": inc.get("descripcionIncidencia", ""),
        })
    events.sort(key=lambda e: e.get("time", ""), reverse=True)

    # ETA: fechaPrimeraEntrega or fCompromiso
    expected_delivery = None
    for date_field in ("fechaPrimeraEntrega", "fCompromiso", "fechaEntrega"):
        val = data.get(date_field, "") or ""
        if val and val.strip():
            # Format: "23/04/2026 00:00:00" -> "2026-04-23"
            parts = val.strip().split(" ")[0].split("/")
            if len(parts) == 3:
                expected_delivery = f"{parts[2]}-{parts[1]}-{parts[0]}"
                break

    last_update = data.get("fechaEstado", "")

    return {
        "status": status,
        "last_status_text": estado_text,
        "last_update": last_update,
        "expected_delivery": expected_delivery,
        "events": events,
    }
