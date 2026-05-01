# 📦 Swiss Delivery Tracker

CLI tool for tracking package deliveries in Switzerland. Supports multiple carriers common for Swiss residents who order from domestic and international shops.

## Supported Carriers

| Carrier | API Type | Auth Required |
|---------|----------|---------------|
| Swiss Post | Direct (unofficial, 4-step CSRF flow) | No |
| Quickpac | Direct API | No |
| Planzer | Direct API | No |
| Cainiao / AliExpress | Direct API | No |
| SunYou | JSONP API | No |
| Hermes Einrichtungs-Service | Direct API | No |
| Spring GDS | PostNL International API | No |
| PostLogistics | Direct API (eosapi) | No |
| Dachser | JSON API | Full tracking URL needed |
| UPS | ⚠️ **Experimental** — CDP browser scraping | Chrome + websocket-client |

Most carriers use free, public APIs with no API keys needed.

## Installation

```bash
pip install git+https://github.com/PLhery/swiss-delivery-tracker.git
```

Or clone and install locally:

```bash
git clone https://github.com/PLhery/swiss-delivery-tracker.git
cd swiss-delivery-tracker
pip install -e .
```

## Usage

### Add a delivery

```bash
swiss-delivery-tracker add --tracking 996014474200248609 --carrier "Swiss Post" --description "New headphones"
swiss-delivery-tracker add -t LP123456789CN -c AliExpress -d "Phone case" --origin CN
swiss-delivery-tracker add -t QP12345678 -c Quickpac -d "Galaxus order"
```

### Update all active deliveries

```bash
swiss-delivery-tracker update
```

### List deliveries

```bash
swiss-delivery-tracker list                # Active only
swiss-delivery-tracker list --status all   # All (except removed)
swiss-delivery-tracker list -s delivered   # Delivered only
```

### Show delivery details

```bash
swiss-delivery-tracker show 996014474200248609
swiss-delivery-tracker show 3                  # By delivery ID
```

### Remove a delivery

```bash
swiss-delivery-tracker remove 996014474200248609
```

## Data Storage

Deliveries are stored in `~/.swiss-delivery-tracker/deliveries.json` by default. Override with:

```bash
swiss-delivery-tracker --data-file /path/to/deliveries.json list
```

## Carrier Notes

- **Swiss Post**: Uses an unofficial 4-step flow with CSRF tokens. Works for all Swiss Post parcels and registered letters.
- **Quickpac**: Also cross-checks Planzer for cross-border ETAs on Quickpac shipments.
- **Cainiao/AliExpress**: Tracks AliExpress parcels via Cainiao's global API. Includes ETA when available.
- **SunYou**: Uses a JSONP endpoint at sypost.net.
- **Dachser**: Uses a JSON API behind the SPA. Requires the full tracking URL with authentication hash (from Dachser email notifications).
- **UPS** ⚠️ **Experimental**: Scrapes ups.com via Chrome DevTools Protocol. Requires a running Chrome with `--remote-debugging-port=18800 --remote-allow-origins=*` and the `websocket-client` Python package. Slow (~20s per lookup) and may break if UPS changes their frontend.
- **Planzer**: Supports Ikea-style order numbers (e.g. `84693.0055089536` extracts `55089536`).

## No Dependencies

This tool uses only Python standard library (`urllib`, `json`, `http.cookiejar`). No `requests`, no `aiohttp`, no heavy packages. Python 3.9+ required.

The **UPS carrier** optionally requires `websocket-client` (`pip install websocket-client`) and a running Chrome instance.

## License

MIT
