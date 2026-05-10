"""Pull EIA hourly data for GridCast.

Hits the EIA API v2 and writes long-format parquet files under
backend/data/raw/:

  - BA-level region-data (D, DF, NG, TI) for PJM, CISO, ERCO
  - Hourly fuel-type generation for the same BAs
  - Sub-BA demand for the Dominion (DOM) zone of PJM

Idempotent: existing files are skipped. Delete to re-pull.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "backend" / "data" / "raw"

BASE_URL = "https://api.eia.gov/v2"
PAGE_SIZE = 5000
MAX_RETRIES = 5
TIMEOUT = 60

START = "2020-01-01T00"  # covers Texas Winter Storm 2021 + all replay events
END = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")

BAS = ["PJM", "CISO", "ERCO"]
REGION_TYPES = ["D", "DF", "NG", "TI"]
FUEL_TYPES = ["COL", "NG", "NUC", "OIL", "SUN", "WAT", "WND", "OTH"]

load_dotenv(ROOT / ".env")
API_KEY = os.environ["EIA_API_KEY"]


def _get(url: str, params: list[tuple[str, str]]) -> dict:
    for attempt in range(MAX_RETRIES):
        r = requests.get(url, params=params, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
            wait = 2 ** attempt
            print(f"  retry {attempt + 1}/{MAX_RETRIES} in {wait}s (status {r.status_code})")
            time.sleep(wait)
            continue
        r.raise_for_status()
    raise RuntimeError("retry budget exhausted")


def _paginated(endpoint: str, base_params: list[tuple[str, str]]) -> list[dict]:
    url = f"{BASE_URL}{endpoint}"
    rows: list[dict] = []
    offset = 0
    while True:
        params = base_params + [("offset", str(offset)), ("length", str(PAGE_SIZE))]
        body = _get(url, params)
        page = body["response"]["data"]
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def _common(start: str, end: str) -> list[tuple[str, str]]:
    return [
        ("api_key", API_KEY),
        ("frequency", "hourly"),
        ("data[0]", "value"),
        ("start", start),
        ("end", end),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "asc"),
    ]


def fetch_region_data(ba: str, start: str, end: str) -> pd.DataFrame:
    params = _common(start, end) + [("facets[respondent][]", ba)]
    for t in REGION_TYPES:
        params.append(("facets[type][]", t))
    rows = _paginated("/electricity/rto/region-data/data/", params)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["period"] = pd.to_datetime(df["period"], utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df[["period", "respondent", "type", "value"]].sort_values(["type", "period"]).reset_index(drop=True)


def fetch_fuel_mix(ba: str, start: str, end: str) -> pd.DataFrame:
    params = _common(start, end) + [("facets[respondent][]", ba)]
    for f in FUEL_TYPES:
        params.append(("facets[fueltype][]", f))
    rows = _paginated("/electricity/rto/fuel-type-data/data/", params)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["period"] = pd.to_datetime(df["period"], utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df[["period", "respondent", "fueltype", "value"]].sort_values(["fueltype", "period"]).reset_index(drop=True)


def fetch_subba_data(parent: str, subba: str, start: str, end: str) -> pd.DataFrame:
    params = _common(start, end) + [
        ("facets[parent][]", parent),
        ("facets[subba][]", subba),
    ]
    rows = _paginated("/electricity/rto/region-sub-ba-data/data/", params)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["period"] = pd.to_datetime(df["period"], utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df[["period", "parent", "subba", "value"]].sort_values("period").reset_index(drop=True)


def _save(path: Path, fetch_fn, label: str) -> None:
    if path.exists():
        print(f"[skip] {path.name}")
        return
    print(f"[pull] {label}")
    df = fetch_fn()
    if df.empty:
        print(f"  WARN: empty result for {label}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    span = f"{df['period'].min()} -> {df['period'].max()}"
    print(f"[ok]   {path.name}  {len(df):,} rows  {span}")


def main() -> None:
    print(f"Window: {START} -> {END}")
    print(f"Output: {RAW_DIR}")
    for ba in BAS:
        _save(
            RAW_DIR / f"eia_{ba.lower()}_demand.parquet",
            lambda ba=ba: fetch_region_data(ba, START, END),
            f"{ba} region-data (D/DF/NG/TI)",
        )
        _save(
            RAW_DIR / f"eia_{ba.lower()}_fuelmix.parquet",
            lambda ba=ba: fetch_fuel_mix(ba, START, END),
            f"{ba} fuel-type-data",
        )
    _save(
        RAW_DIR / "eia_pjm_dom_demand.parquet",
        lambda: fetch_subba_data("PJM", "DOM", START, END),
        "PJM/DOM sub-BA demand",
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
