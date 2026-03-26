#!/usr/bin/env python3
"""
Runs once daily after US market close.
Fetches VIX historical (1d/1y) and VIX 50-day SMA from FRED.
"""

import json
import os
import time
from datetime import datetime, timezone, timedelta

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
YAHOO_BASE    = "https://query1.finance.yahoo.com/v8/finance/chart/"
FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"
FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_API_KEY  = os.environ.get("FRED_API_KEY", "")
VIX_SYMBOL    = "%5EVIX"


def save(path: str, data: object):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    size_kb = os.path.getsize(path) // 1024
    print(f"  Saved {path} ({size_kb} KB)")


def parse_fred_csv(text: str) -> list:
    lines = text.strip().splitlines()
    result = []
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        val_str = parts[1].strip()
        if not val_str or val_str == ".":
            continue
        try:
            dt = datetime.strptime(parts[0].strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            result.append({"x": int(dt.timestamp() * 1000), "y": float(val_str)})
        except (ValueError, IndexError):
            continue
    return sorted(result, key=lambda p: p["x"])


def fetch_fred(series: str, start_date: str) -> list:
    if FRED_API_KEY:
        r = requests.get(
            FRED_API_BASE,
            params={
                "series_id": series, "observation_start": start_date,
                "file_type": "json", "api_key": FRED_API_KEY,
            },
            headers=HEADERS, timeout=20,
        )
        r.raise_for_status()
        obs = r.json().get("observations", [])
        result = []
        for o in obs:
            val_str = o.get("value", ".")
            if not val_str or val_str == ".":
                continue
            try:
                dt = datetime.strptime(o["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                result.append({"x": int(dt.timestamp() * 1000), "y": float(val_str)})
            except (ValueError, KeyError):
                continue
        return sorted(result, key=lambda p: p["x"])

    r = requests.get(
        FRED_CSV_BASE,
        params={"id": series, "observation_start": start_date},
        headers=HEADERS, timeout=20,
    )
    r.raise_for_status()
    return parse_fred_csv(r.text)


def calculate_sma(data: list, period: int) -> list:
    result = []
    for i in range(len(data)):
        if i < period - 1:
            continue
        window = data[i - period + 1: i + 1]
        result.append({"x": data[i]["x"], "y": sum(p["y"] for p in window) / period})
    return result


def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"=== fetch_daily.py  {ts} ===")
    now = datetime.now(timezone.utc)

    # VIX historical (1d/1y)
    print("VIX historical (1d/1y)...")
    try:
        r = requests.get(
            f"{YAHOO_BASE}{VIX_SYMBOL}",
            params={"interval": "1d", "range": "1y"},
            headers=HEADERS, timeout=20,
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
        save("data/vix-historical.json", points)
    except Exception as e:
        print(f"  ERROR VIX historical: {e}")
    time.sleep(0.5)

    # VIX 50-day SMA (FRED VIXCLS, 3 years)
    print("VIX 50d SMA (FRED VIXCLS)...")
    try:
        start = (now - timedelta(days=3 * 365)).strftime("%Y-%m-%d")
        points = fetch_fred("VIXCLS", start)
        sma50 = calculate_sma(points, 50)
        save("data/vix-sma.json", sma50)
    except Exception as e:
        print(f"  ERROR VIX SMA: {e}")

    print("=== Done ===")


if __name__ == "__main__":
    main()
