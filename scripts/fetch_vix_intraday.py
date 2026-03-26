#!/usr/bin/env python3
"""
Fetches VIX 1-minute intraday chart only.
Called in a tight loop inside the workflow for near-realtime updates.
"""

import json
import os
from datetime import datetime, timezone

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
VIX_SYMBOL = "%5EVIX"
YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"


def save(path: str, data: object):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    size_kb = os.path.getsize(path) // 1024
    print(f"  Saved {path} ({size_kb} KB)")


def main():
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    print(f"VIX intraday fetch @ {ts}")
    try:
        r = requests.get(
            f"{YAHOO_BASE}{VIX_SYMBOL}",
            params={"interval": "1m", "range": "1d"},
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        result = r.json()["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        points = [
            {"x": int(ts) * 1000, "y": round(float(c), 4)}
            for ts, c in zip(timestamps, closes)
            if c is not None
        ]
        save("data/vix-intraday.json", points)
    except Exception as e:
        print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()
