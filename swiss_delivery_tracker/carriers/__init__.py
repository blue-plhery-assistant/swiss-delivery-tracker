"""Carrier modules for Swiss Delivery Tracker."""

import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
import json

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def make_opener():
    """Create a urllib opener with cookie support."""
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def json_request(url, headers=None, data=None, method=None, timeout=15):
    """Make an HTTP request and return parsed JSON."""
    hdrs = {**BASE_HEADERS, **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))
