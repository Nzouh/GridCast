"""Build model-ready hourly feature tables for GridCast.

Inputs live under backend/data/raw/ and are produced by pull_eia.py and
pull_weather.py. Outputs land in backend/data/processed/.

The target is demand_mw. Weather and calendar fields are known or forecastable
future inputs; lagged demand fields are observed-past inputs for the TFT.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "backend" / "data" / "raw"
PROCESSED_DIR = ROOT / "backend" / "data" / "processed"

MIN_RECOMMENDED_START = pd.Timestamp("2020-01-01", tz="UTC")

NODES = {
    "dominion_hub": {
        "node_id": "dominion-hub",
        "demand_path": "eia_pjm_dom_demand.parquet",
        "weather_path": "weather_dominion_hub.parquet",
        "ba_code": "PJM",
        "demand_scale": 1.00,
    },
    "caiso_sp15": {
        "node_id": "caiso-sp15",
        "demand_path": "eia_ciso_demand.parquet",
        "weather_path": "weather_caiso_sp15.parquet",
        "ba_code": "CISO",
        "demand_scale": 0.72,
    },
    "caiso_np15": {
        "node_id": "caiso-np15",
        "demand_path": "eia_ciso_demand.parquet",
        "weather_path": "weather_caiso_np15.parquet",
        "ba_code": "CISO",
        "demand_scale": 0.45,
    },
    "ercot_houston": {
        "node_id": "ercot-houston",
        "demand_path": "eia_erco_demand.parquet",
        "weather_path": "weather_ercot_houston.parquet",
        "ba_code": "ERCO",
        "demand_scale": 0.25,
    },
}

WEATHER_FEATURES = [
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

LAG_HOURS = [1, 24, 168]
ROLLING_WINDOWS = [24, 168]


def read_demand(path: Path, ba_code: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["period"] = pd.to_datetime(df["period"], utc=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    if "type" in df.columns:
        demand = df[df["type"] == "D"][["period", "value"]].copy()
        forecast = df[df["type"] == "DF"][["period", "value"]].rename(columns={"value": "eia_demand_forecast_mw"})
        demand = demand.merge(forecast, on="period", how="left")
    else:
        demand = df[["period", "value"]].copy()
        demand["eia_demand_forecast_mw"] = float("nan")

    demand = demand.rename(columns={"value": "demand_mw"})
    demand["demand_mw"] = pd.to_numeric(demand["demand_mw"], errors="coerce")
    demand["eia_demand_forecast_mw"] = pd.to_numeric(demand["eia_demand_forecast_mw"], errors="coerce")
    demand["ba_code"] = ba_code
    return demand.sort_values("period").drop_duplicates("period")


def read_weather(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["period"] = pd.to_datetime(df["period"], utc=True)
    keep = ["period", *[c for c in WEATHER_FEATURES if c in df.columns]]
    weather = df[keep].copy()
    for col in keep:
        if col != "period":
            weather[col] = pd.to_numeric(weather[col], errors="coerce")
    return weather.sort_values("period").drop_duplicates("period")


def add_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ts = out["period"].dt
    hour = ts.hour
    day_of_week = ts.dayofweek
    day_of_year = ts.dayofyear
    month = ts.month

    out["hour"] = hour
    out["day_of_week"] = day_of_week
    out["month"] = month
    out["is_weekend"] = day_of_week.isin([5, 6]).astype("int8")
    out["hour_sin"] = (2 * math.pi * hour / 24).map(math.sin)
    out["hour_cos"] = (2 * math.pi * hour / 24).map(math.cos)
    out["dow_sin"] = (2 * math.pi * day_of_week / 7).map(math.sin)
    out["dow_cos"] = (2 * math.pi * day_of_week / 7).map(math.cos)
    out["doy_sin"] = (2 * math.pi * day_of_year / 366).map(math.sin)
    out["doy_cos"] = (2 * math.pi * day_of_year / 366).map(math.cos)
    return out


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("period").copy()
    for lag in LAG_HOURS:
        out[f"demand_lag_{lag}h"] = out["demand_mw"].shift(lag)
    for window in ROLLING_WINDOWS:
        shifted = out["demand_mw"].shift(1)
        out[f"demand_roll_mean_{window}h"] = shifted.rolling(window, min_periods=window).mean()
        out[f"demand_roll_std_{window}h"] = shifted.rolling(window, min_periods=window).std()
    return out


def build_node_features(raw_node_id: str, cfg: dict[str, str | float]) -> pd.DataFrame:
    demand = read_demand(RAW_DIR / cfg["demand_path"], cfg["ba_code"])
    weather = read_weather(RAW_DIR / cfg["weather_path"])

    merged = demand.merge(weather, on="period", how="inner")
    merged.insert(0, "node_id", cfg["node_id"])
    merged["raw_ba_demand_mw"] = merged["demand_mw"]
    merged["raw_ba_demand_forecast_mw"] = merged["eia_demand_forecast_mw"]
    scale = float(cfg["demand_scale"])
    merged["demand_mw"] = merged["raw_ba_demand_mw"] * scale
    merged["eia_demand_forecast_mw"] = merged["raw_ba_demand_forecast_mw"] * scale
    merged = add_calendar_features(merged)
    merged = add_lag_features(merged)

    before = len(merged)
    required = ["demand_mw", *[f"demand_lag_{lag}h" for lag in LAG_HOURS]]
    merged = merged.dropna(subset=required).reset_index(drop=True)
    dropped = before - len(merged)

    span = f"{merged['period'].min()} -> {merged['period'].max()}" if not merged.empty else "empty"
    print(f"[ok] {raw_node_id:<15} {len(merged):>6,} rows  {span}  dropped={dropped}")
    return merged


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []

    print(f"Raw:       {RAW_DIR}")
    print(f"Processed: {PROCESSED_DIR}\n")

    for raw_node_id, cfg in NODES.items():
        df = build_node_features(raw_node_id, cfg)
        if df.empty:
            continue
        frames.append(df)
        df.to_parquet(PROCESSED_DIR / f"{raw_node_id}.parquet", index=False)

    if not frames:
        raise RuntimeError("No feature rows were produced.")

    all_nodes = pd.concat(frames, ignore_index=True)
    all_nodes.to_parquet(PROCESSED_DIR / "all_nodes.parquet", index=False)

    start = all_nodes["period"].min()
    end = all_nodes["period"].max()
    print(f"\n[ok] all_nodes.parquet {len(all_nodes):,} rows  {start} -> {end}")

    if start > MIN_RECOMMENDED_START:
        print(
            "\nWARN: processed data starts after 2020-01-01. "
            "For Texas 2021/PJM 2023 replay training, delete old raw parquets "
            "and re-run pull_eia.py + pull_weather.py."
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
