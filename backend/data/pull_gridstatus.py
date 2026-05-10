"""Pull hourly LMP / SPP for the 4 GridCast nodes via gridstatus.

For each node, fetches both Day-Ahead (DAM) and Real-Time (RTM) prices.
Imbalance cost = (actual_demand - forecast_demand) * (RTM_price - DAM_price),
so we need both markets.

Outputs (long format):
  lmp_ercot_houston.parquet  — Houston Hub (HB_HOUSTON)
  lmp_caiso_sp15.parquet     — SP15 trading hub
  lmp_caiso_np15.parquet     — NP15 trading hub
  lmp_pjm_dominion.parquet   — Dominion zone hub

Schema: period (UTC), node, market ('DAM'|'RTM'), price ($/MWh).

Idempotent. Pulls are slow — ERCOT's full 2020→today is the longest
(~5–10 min). Comment out entries in NODES at the bottom to skip ISOs.

If a specific ISO fails (API change, rate limit, network), it is logged
and the script moves on. Re-run later to fill gaps; existing files are
preserved.
"""
from __future__ import annotations

import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "backend" / "data" / "raw"

START = "2020-01-01"
END = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _to_hourly_utc(df: pd.DataFrame, time_col: str, price_col: str) -> pd.DataFrame:
    """Normalize a gridstatus result to hourly UTC mean.

    gridstatus returns timestamps as tz-aware. We standardize to UTC and,
    if the source is sub-hourly (5-min, 15-min), aggregate to hourly mean.
    """
    df = df[[time_col, price_col]].copy()
    df[time_col] = pd.to_datetime(df[time_col], utc=True)
    df = df.set_index(time_col).sort_index()
    df = df.resample("1h").mean()
    df = df.reset_index().rename(columns={time_col: "period", price_col: "price"})
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    return df


def _wrap(node: str, market: str, df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.insert(1, "node", node)
    df.insert(2, "market", market)
    return df[["period", "node", "market", "price"]]


def fetch_ercot(node: str, hub: str, start: str, end: str) -> pd.DataFrame:
    import gridstatus
    iso = gridstatus.Ercot()
    print(f"  ERCOT DAM SPP for {hub} ...")
    dam = iso.get_spp(date=start, end=end, location_type="Trading Hub", market="DAY_AHEAD_HOURLY")
    dam = dam[dam["Location"] == hub]
    dam = _to_hourly_utc(dam, "Time", "SPP")
    print(f"  ERCOT RTM SPP for {hub} ...")
    rtm = iso.get_spp(date=start, end=end, location_type="Trading Hub", market="REAL_TIME_15_MIN")
    rtm = rtm[rtm["Location"] == hub]
    rtm = _to_hourly_utc(rtm, "Time", "SPP")
    return pd.concat([_wrap(node, "DAM", dam), _wrap(node, "RTM", rtm)], ignore_index=True)


def fetch_caiso(node: str, hub: str, start: str, end: str) -> pd.DataFrame:
    import gridstatus
    iso = gridstatus.CAISO()
    print(f"  CAISO DAM LMP for {hub} ...")
    dam = iso.get_lmp(date=start, end=end, market="DAY_AHEAD_HOURLY", locations=[hub])
    dam = _to_hourly_utc(dam, "Time", "LMP")
    print(f"  CAISO RTM LMP for {hub} ...")
    rtm = iso.get_lmp(date=start, end=end, market="REAL_TIME_HOURLY", locations=[hub])
    rtm = _to_hourly_utc(rtm, "Time", "LMP")
    return pd.concat([_wrap(node, "DAM", dam), _wrap(node, "RTM", rtm)], ignore_index=True)


def fetch_pjm(node: str, hub: str, start: str, end: str) -> pd.DataFrame:
    import gridstatus
    iso = gridstatus.PJM()
    print(f"  PJM DAM LMP for {hub} ...")
    dam = iso.get_lmp(date=start, end=end, market="DAY_AHEAD_HOURLY", locations=[hub])
    dam = _to_hourly_utc(dam, "Time", "Total LMP DA")
    print(f"  PJM RTM LMP for {hub} ...")
    rtm = iso.get_lmp(date=start, end=end, market="REAL_TIME_HOURLY", locations=[hub])
    rtm = _to_hourly_utc(rtm, "Time", "Total LMP RT")
    return pd.concat([_wrap(node, "DAM", dam), _wrap(node, "RTM", rtm)], ignore_index=True)


NODES = [
    # (node_id, fetch_fn, hub_label)
    ("ercot_houston", fetch_ercot, "HB_HOUSTON"),
    ("caiso_sp15",    fetch_caiso, "TH_SP15_GEN-APND"),
    ("caiso_np15",    fetch_caiso, "TH_NP15_GEN-APND"),
    ("pjm_dominion",  fetch_pjm,   "DOMINION HUB"),
]


def main() -> None:
    print(f"Window: {START} -> {END}")
    print(f"Output: {RAW_DIR}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for node_id, fetch_fn, hub in NODES:
        out = RAW_DIR / f"lmp_{node_id}.parquet"
        if out.exists():
            print(f"[skip] {out.name}")
            continue
        print(f"--- {node_id}  hub={hub} ---")
        t0 = time.time()
        try:
            df = fetch_fn(node_id, hub, START, END)
            if df.empty:
                print(f"[warn] empty result for {node_id}")
                continue
            df.to_parquet(out, index=False)
            span = f"{df['period'].min()} -> {df['period'].max()}"
            took = time.time() - t0
            print(f"[ok]   {out.name}  {len(df):,} rows  {span}  ({took:.0f}s)")
        except Exception as exc:
            print(f"[FAIL] {node_id}: {exc.__class__.__name__}: {exc}")
            traceback.print_exc(limit=2)
            print("       continuing with next node — re-run later to retry")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
