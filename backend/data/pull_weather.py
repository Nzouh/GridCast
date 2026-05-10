"""Pull Open-Meteo weather for GridCast nodes.

Two pulls per node:
  - Historical archive (ERA5 reanalysis), 2024-05-01 -> today: training data
  - 10-day GFS ensemble forecast: live demo inputs (probabilistic weather)

No API key required. Outputs wide-format parquet under backend/data/raw/.

Historical pulls are idempotent (skip if file exists).
Forecast pulls always overwrite — re-run before each demo for fresh data.

Coordinates are picked at the demand-center anchor for each node:
  Dominion Hub  -> Ashburn, VA (the data-center cluster)
  CAISO SP15    -> downtown LA
  CAISO NP15    -> San Francisco
  ERCOT Houston -> downtown Houston
Open-Meteo grids weather to ~10km globally so any lat/lon resolves.
"""
from __future__ import annotations

import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "backend" / "data" / "raw"

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
ENSEMBLE_URL = "https://ensemble-api.open-meteo.com/v1/ensemble"

START_DATE = "2020-01-01"  # covers Texas Winter Storm 2021 + all replay events
END_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
FORECAST_DAYS = 10
ENSEMBLE_MODEL = "gfs05"  # GFS Ensemble System, 31 members, ~50km

MAX_RETRIES = 5
TIMEOUT = 120

NODES = {
    "dominion_hub":  {"lat": 39.0438,  "lon": -77.4874,  "label": "Dominion Hub (Ashburn, VA)"},
    "caiso_sp15":    {"lat": 34.0522,  "lon": -118.2437, "label": "CAISO SP15 (Los Angeles, CA)"},
    "caiso_np15":    {"lat": 37.7749,  "lon": -122.4194, "label": "CAISO NP15 (San Francisco, CA)"},
    "ercot_houston": {"lat": 29.7604,  "lon": -95.3698,  "label": "ERCOT Houston Hub (Houston, TX)"},
}

HOURLY_VARS = [
    "temperature_2m",
    "dewpoint_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "cloud_cover",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "precipitation",
]


def _get(url: str, params: dict) -> dict:
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


def fetch_historical(node_id: str, lat: float, lon: float, start: str, end: str) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "UTC",
    }
    body = _get(ARCHIVE_URL, params)
    h = body.get("hourly", {})
    if not h:
        return pd.DataFrame()

    times = pd.to_datetime(h.pop("time"), utc=True)
    df = pd.DataFrame(h)
    df.insert(0, "period", times)
    df.insert(0, "node", node_id)
    return df


def fetch_forecast_ensemble(node_id: str, lat: float, lon: float, days: int) -> pd.DataFrame:
    """Returns long-on-member, wide-on-variable.

    Open-Meteo packs ensemble members as `<var>_memberNN` columns in `hourly`.
    Member 0 is the control run (the bare `<var>` column).
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY_VARS),
        "models": ENSEMBLE_MODEL,
        "forecast_days": days,
        "timezone": "UTC",
    }
    body = _get(ENSEMBLE_URL, params)
    h = body.get("hourly", {})
    if not h:
        return pd.DataFrame()

    times = pd.to_datetime(h.pop("time"), utc=True)
    pattern = re.compile(r"^(.+?)(?:_member(\d+))?$")

    members: dict[int, dict[str, list]] = {}
    for col, values in h.items():
        m = pattern.match(col)
        if not m:
            continue
        var, member_str = m.group(1), m.group(2)
        if var not in HOURLY_VARS:
            continue
        member_id = int(member_str) if member_str else 0
        members.setdefault(member_id, {})[var] = values

    if not members:
        return pd.DataFrame()

    frames = []
    fetched_at = datetime.now(timezone.utc).isoformat()
    for member_id in sorted(members):
        f = pd.DataFrame(members[member_id])
        f.insert(0, "period", times)
        f.insert(0, "member", member_id)
        f.insert(0, "node", node_id)
        f["fetched_at"] = fetched_at
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def _save(path: Path, fetch_fn, label: str, force: bool = False) -> None:
    if path.exists() and not force:
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
    extra = f"  members={df['member'].nunique()}" if "member" in df.columns else ""
    print(f"[ok]   {path.name}  {len(df):,} rows  {span}{extra}")


def main() -> None:
    print(f"Historical window: {START_DATE} -> {END_DATE}")
    print(f"Forecast horizon:  {FORECAST_DAYS} days, model={ENSEMBLE_MODEL}")
    print(f"Output: {RAW_DIR}\n")

    for node_id, info in NODES.items():
        lat, lon, label = info["lat"], info["lon"], info["label"]
        print(f"--- {label} ({lat}, {lon}) ---")
        _save(
            RAW_DIR / f"weather_{node_id}.parquet",
            lambda nid=node_id, la=lat, lo=lon: fetch_historical(nid, la, lo, START_DATE, END_DATE),
            f"{node_id} historical",
        )
        _save(
            RAW_DIR / f"weather_forecast_{node_id}.parquet",
            lambda nid=node_id, la=lat, lo=lon: fetch_forecast_ensemble(nid, la, lo, FORECAST_DAYS),
            f"{node_id} ensemble forecast",
            force=True,
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
