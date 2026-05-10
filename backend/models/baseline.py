"""Evaluate simple demand forecasting baselines.

This is the bar the TFT must beat. The main baseline is seasonal naive:
forecast demand at time t as demand at t - 168h.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_PATH = ROOT / "backend" / "data" / "processed" / "all_nodes.parquet"
OUT_DIR = ROOT / "backend" / "models" / "out"

TEST_DAYS = 60
EPS = 1e-9


def mape(actual: pd.Series, predicted: pd.Series) -> float:
    return float(((actual - predicted).abs() / actual.clip(lower=EPS)).mean() * 100)


def mae(actual: pd.Series, predicted: pd.Series) -> float:
    return float((actual - predicted).abs().mean())


def rmse(actual: pd.Series, predicted: pd.Series) -> float:
    return float(((actual - predicted) ** 2).mean() ** 0.5)


def evaluate_one(df: pd.DataFrame, pred_col: str) -> dict[str, float | int | str]:
    actual = df["demand_mw"]
    predicted = df[pred_col]
    return {
        "n": int(len(df)),
        "mae_mw": round(mae(actual, predicted), 2),
        "rmse_mw": round(rmse(actual, predicted), 2),
        "mape_pct": round(mape(actual, predicted), 3),
        "bias_mw": round(float((predicted - actual).mean()), 2),
    }


def add_baselines(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["node_id", "period"]).copy()
    out["seasonal_naive_168h_mw"] = out.groupby("node_id")["demand_mw"].shift(168)
    out["persistence_24h_mw"] = out.groupby("node_id")["demand_mw"].shift(24)
    return out


def test_window(df: pd.DataFrame) -> pd.DataFrame:
    cutoff = df["period"].max() - pd.Timedelta(days=TEST_DAYS)
    return df[df["period"] > cutoff].copy()


def build_metrics(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    candidate_cols = [
        ("seasonal_naive_168h", "seasonal_naive_168h_mw"),
        ("persistence_24h", "persistence_24h_mw"),
    ]

    if df["eia_demand_forecast_mw"].notna().any():
        candidate_cols.append(("eia_day_ahead", "eia_demand_forecast_mw"))

    for node_id, node_df in df.groupby("node_id", sort=True):
        for name, col in candidate_cols:
            usable = node_df.dropna(subset=["demand_mw", col])
            if usable.empty:
                continue
            row = {"node_id": node_id, "baseline": name}
            row.update(evaluate_one(usable, col))
            rows.append(row)

    for name, col in candidate_cols:
        usable = df.dropna(subset=["demand_mw", col])
        if usable.empty:
            continue
        row = {"node_id": "ALL", "baseline": name}
        row.update(evaluate_one(usable, col))
        rows.append(row)

    return pd.DataFrame(rows)


def main() -> None:
    if not PROCESSED_PATH.exists():
        raise FileNotFoundError(f"Missing {PROCESSED_PATH}. Run backend/data/build_features.py first.")

    df = pd.read_parquet(PROCESSED_PATH)
    df["period"] = pd.to_datetime(df["period"], utc=True)
    df = add_baselines(df)
    test = test_window(df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = build_metrics(test).sort_values(["node_id", "mape_pct", "baseline"])
    metrics.to_csv(OUT_DIR / "baseline_metrics.csv", index=False)

    predictions = test[
        [
            "node_id",
            "period",
            "demand_mw",
            "seasonal_naive_168h_mw",
            "persistence_24h_mw",
            "eia_demand_forecast_mw",
        ]
    ].copy()
    predictions.to_parquet(OUT_DIR / "baseline_predictions.parquet", index=False)

    span = f"{test['period'].min()} -> {test['period'].max()}"
    print(f"Evaluation window: {span} ({len(test):,} rows)")
    print(f"Outputs: {OUT_DIR}")
    print()
    print(metrics.to_string(index=False))
    print()
    best = metrics[metrics["node_id"] == "ALL"].sort_values("mape_pct").head(1)
    if not best.empty:
        row = best.iloc[0]
        print(f"Best overall baseline: {row['baseline']}  MAPE={row['mape_pct']}%  MAE={row['mae_mw']} MW")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
