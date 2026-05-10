"""Calibrate TFT demand quantiles using held-out validation predictions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "backend" / "models" / "out"
PREDICTIONS_PATH = OUT_DIR / "tft_predictions.parquet"

QUANTILES = {
    "p10": 0.10,
    "p25": 0.25,
    "p50": 0.50,
    "p75": 0.75,
    "p90": 0.90,
}

HORIZON_BUCKETS = [
    (1, 24, "001-024h"),
    (25, 72, "025-072h"),
    (73, 168, "073-168h"),
    (169, 240, "169-240h"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, default=PREDICTIONS_PATH)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--min-group-rows", type=int, default=1000)
    return parser.parse_args()


def horizon_bucket(lead_hour: int) -> str:
    for start, end, label in HORIZON_BUCKETS:
        if start <= lead_hour <= end:
            return label
    return "other"


def empirical_corrections(df: pd.DataFrame) -> dict[str, float]:
    corrections = {}
    actual = df["actual_demand_mw"]
    for col, quantile in QUANTILES.items():
        residual = actual - df[col]
        corrections[col] = round(float(residual.quantile(quantile)), 3)
    return corrections


def apply_corrections(df: pd.DataFrame, corrections: dict[str, float], suffix: str = "_cal") -> pd.DataFrame:
    out = df.copy()
    calibrated = np.column_stack([out[col].to_numpy(dtype=float) + corrections[col] for col in QUANTILES])
    calibrated = np.maximum.accumulate(calibrated, axis=1)
    for idx, col in enumerate(QUANTILES):
        out[f"{col}{suffix}"] = calibrated[:, idx]
    return out


def interval_coverage(df: pd.DataFrame, lower: str, upper: str) -> float:
    actual = df["actual_demand_mw"]
    return float(((actual >= df[lower]) & (actual <= df[upper])).mean() * 100)


def quantile_hit_rate(df: pd.DataFrame, col: str) -> float:
    return float((df["actual_demand_mw"] <= df[col]).mean() * 100)


def mean_width(df: pd.DataFrame, lower: str, upper: str) -> float:
    return float((df[upper] - df[lower]).mean())


def build_metrics(df: pd.DataFrame, node_id: str, bucket: str) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "horizon_bucket": bucket,
        "n": int(len(df)),
        "p10_hit_pct": round(quantile_hit_rate(df, "p10_cal"), 2),
        "p25_hit_pct": round(quantile_hit_rate(df, "p25_cal"), 2),
        "p50_hit_pct": round(quantile_hit_rate(df, "p50_cal"), 2),
        "p75_hit_pct": round(quantile_hit_rate(df, "p75_cal"), 2),
        "p90_hit_pct": round(quantile_hit_rate(df, "p90_cal"), 2),
        "p10_p90_coverage_pct": round(interval_coverage(df, "p10_cal", "p90_cal"), 2),
        "p25_p75_coverage_pct": round(interval_coverage(df, "p25_cal", "p75_cal"), 2),
        "mean_p90_p10_width_mw": round(mean_width(df, "p10_cal", "p90_cal"), 2),
        "mean_p75_p25_width_mw": round(mean_width(df, "p25_cal", "p75_cal"), 2),
    }


def build_uncalibrated_metrics(df: pd.DataFrame) -> dict[str, float]:
    return {
        "p10_hit_pct": round(quantile_hit_rate(df, "p10"), 2),
        "p25_hit_pct": round(quantile_hit_rate(df, "p25"), 2),
        "p50_hit_pct": round(quantile_hit_rate(df, "p50"), 2),
        "p75_hit_pct": round(quantile_hit_rate(df, "p75"), 2),
        "p90_hit_pct": round(quantile_hit_rate(df, "p90"), 2),
        "p10_p90_coverage_pct": round(interval_coverage(df, "p10", "p90"), 2),
        "p25_p75_coverage_pct": round(interval_coverage(df, "p25", "p75"), 2),
        "mean_p90_p10_width_mw": round(mean_width(df, "p10", "p90"), 2),
        "mean_p75_p25_width_mw": round(mean_width(df, "p25", "p75"), 2),
    }


def main() -> None:
    args = parse_args()
    if not args.predictions.exists():
        raise FileNotFoundError(f"Missing {args.predictions}. Run backend/models/evaluate_tft.py first.")

    predictions = pd.read_parquet(args.predictions)
    predictions = predictions.dropna(subset=["actual_demand_mw", *QUANTILES.keys()]).copy()
    predictions["horizon_bucket"] = predictions["lead_hour"].map(horizon_bucket)

    global_corrections = empirical_corrections(predictions)
    group_rows: list[dict[str, Any]] = []
    calibrated_parts: list[pd.DataFrame] = []

    for (node_id, bucket), group_df in predictions.groupby(["node_id", "horizon_bucket"], sort=True):
        if len(group_df) < args.min_group_rows:
            corrections = global_corrections
            correction_scope = "global_fallback"
        else:
            corrections = empirical_corrections(group_df)
            correction_scope = "node_horizon"

        calibrated = apply_corrections(group_df, corrections)
        calibrated_parts.append(calibrated)

        row = {
            "node_id": str(node_id),
            "horizon_bucket": str(bucket),
            "n": int(len(group_df)),
            "correction_scope": correction_scope,
            **{f"{col}_correction_mw": corrections[col] for col in QUANTILES},
        }
        row.update({f"before_{key}": value for key, value in build_uncalibrated_metrics(group_df).items()})
        row.update({f"after_{key}": value for key, value in build_metrics(calibrated, str(node_id), str(bucket)).items() if key not in {"node_id", "horizon_bucket", "n"}})
        group_rows.append(row)

    calibrated_predictions = pd.concat(calibrated_parts, ignore_index=True)
    overall_before = build_uncalibrated_metrics(predictions)
    overall_after = build_metrics(calibrated_predictions, "ALL", "ALL")

    artifact = {
        "method": "empirical_residual_quantile_shift",
        "description": (
            "For each node/horizon bucket, add the empirical validation residual quantile "
            "to each TFT quantile. Example: p90_cal = p90 + quantile(actual - p90, 0.90)."
        ),
        "source_predictions": str(args.predictions),
        "quantiles": QUANTILES,
        "horizon_buckets": [
            {"start_lead_hour": start, "end_lead_hour": end, "label": label}
            for start, end, label in HORIZON_BUCKETS
        ],
        "global_corrections_mw": global_corrections,
        "overall_before": overall_before,
        "overall_after": {key: value for key, value in overall_after.items() if key not in {"node_id", "horizon_bucket", "n"}},
        "groups": [
            {
                "node_id": row["node_id"],
                "horizon_bucket": row["horizon_bucket"],
                "n": row["n"],
                "correction_scope": row["correction_scope"],
                "corrections_mw": {col: row[f"{col}_correction_mw"] for col in QUANTILES},
            }
            for row in group_rows
        ],
    }

    args.out.mkdir(parents=True, exist_ok=True)
    calibration_path = args.out / "tft_calibration.json"
    metrics_path = args.out / "tft_calibration_metrics.csv"
    calibrated_path = args.out / "tft_calibrated_predictions.parquet"

    calibration_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(group_rows).sort_values(["node_id", "horizon_bucket"]).to_csv(metrics_path, index=False)
    calibrated_predictions.to_parquet(calibrated_path, index=False)

    print(f"Input rows: {len(predictions):,}")
    print(f"Calibration artifact: {calibration_path}")
    print(f"Metrics: {metrics_path}")
    print(f"Calibrated predictions: {calibrated_path}")
    print()
    print("Overall before:")
    print(pd.DataFrame([overall_before]).to_string(index=False))
    print()
    print("Overall after:")
    print(pd.DataFrame([{key: value for key, value in overall_after.items() if key not in {'node_id', 'horizon_bucket'}}]).to_string(index=False))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
