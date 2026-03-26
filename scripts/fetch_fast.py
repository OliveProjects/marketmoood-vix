#!/usr/bin/env python3
"""
Runs once per 5-minute workflow cycle.
Fetches Fear & Greed index and VIX weekly (60m/5d).
VIX intraday is handled separately in the loop (fetch_vix_intraday.py).
"""

import json
import os
import time
from datetime import datetime, timezone

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
VIX_SYMBOL = "%5EVIX"


def save(path: str, data: object):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    size_kb = os.path.getsize(path) // 1024
    print(f"  Saved {path} ({size_kb} KB)")


def fetch_fear_greed() -> dict | None:
    try:
        r = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/",
            headers={**HEADERS, "Referer": "https://money.cnn.com/data/fear-and-greed/"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ERROR Fear & Greed: {e}")
        return None


def fetch_yahoo_chart(symbol: str, interval: str, range_: str) -> list | None:
    try:
        r = requests.get(
            f"{YAHOO_BASE}{symbol}",
            params={"interval": interval, "range": range_},
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        result = r.json()["chart"]["result"][0]
        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        return [
            {"x": int(ts) * 1000, "y": round(float(c), 4)}
            for ts, c in zip(timestamps, closes)
            if c is not None
        ]
    except Exception as e:
        print(f"  ERROR {symbol} {interval}/{range_}: {e}")
        return None


def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"=== fetch_fast.py  {ts} ===")

    print("Fear & Greed...")
    fg = fetch_fear_greed()
    if fg:
        save("data/fear-greed.json", fg)

    time.sleep(0.3)

    print("VIX weekly (60m/5d)...")
    vix_weekly = fetch_yahoo_chart(VIX_SYMBOL, "60m", "5d")
    if vix_weekly:
        save("data/vix-weekly.json", vix_weekly)

    print("=== Done ===")


if __name__ == "__main__":
    main()
