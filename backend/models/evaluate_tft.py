"""Evaluate a trained GridCast TFT checkpoint against simple baselines."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import train_tft

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "backend" / "models" / "out"
TFT_OUT_DIR = OUT_DIR / "tft"
EPS = 1e-9

HORIZON_BUCKETS = [
    (1, 24, "001-024h"),
    (25, 72, "025-072h"),
    (73, 168, "073-168h"),
    (169, 240, "169-240h"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=train_tft.PROCESSED_PATH)
    parser.add_argument("--checkpoint", type=Path, default=None, help="TFT checkpoint. Defaults to training metadata.")
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--limit-predict-batches", type=float, default=None)
    parser.add_argument("--train-days", type=int, default=None, help="Override training window used to rebuild dataset.")
    return parser.parse_args()


def load_metadata(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "training_metadata.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_checkpoint(args: argparse.Namespace, metadata: dict[str, Any]) -> Path:
    if args.checkpoint is not None:
        checkpoint = args.checkpoint
    elif metadata.get("best_model_path"):
        checkpoint = Path(metadata["best_model_path"])
    else:
        candidates = sorted((TFT_OUT_DIR / "checkpoints").glob("*.ckpt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise FileNotFoundError("No TFT checkpoint found. Run backend/models/train_tft.py first.")
        checkpoint = candidates[0]

    if not checkpoint.exists():
        raise FileNotFoundError(f"Missing checkpoint: {checkpoint}")
    return checkpoint


def add_baselines(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["node_id", "period"]).copy()
    out["seasonal_naive_168h_mw"] = out.groupby("node_id")["demand_mw"].shift(168)
    out["persistence_24h_mw"] = out.groupby("node_id")["demand_mw"].shift(24)
    return out


def flatten_predictions(prediction: Any) -> pd.DataFrame:
    quantiles = prediction.output.detach().cpu().numpy()
    decoder_time_idx = prediction.x["decoder_time_idx"].detach().cpu().numpy()
    decoder_lengths = prediction.decoder_lengths
    if decoder_lengths is None:
        decoder_lengths = prediction.x["decoder_lengths"]
    decoder_lengths = decoder_lengths.detach().cpu().numpy()
    index = prediction.index.reset_index(drop=True)

    n_windows, horizon, _ = quantiles.shape
    forecast_start = index["time_idx"].to_numpy()
    node_ids = index["node_id"].astype(str).to_numpy()
    lead_hour = np.tile(np.arange(1, horizon + 1, dtype=np.int16), n_windows)
    mask = lead_hour <= np.repeat(decoder_lengths, horizon)

    out = pd.DataFrame(
        {
            "node_id": np.repeat(node_ids, horizon),
            "forecast_start_time_idx": np.repeat(forecast_start, horizon),
            "target_time_idx": decoder_time_idx.reshape(-1),
            "lead_hour": lead_hour,
            "p10": quantiles[:, :, 0].reshape(-1),
            "p25": quantiles[:, :, 1].reshape(-1),
            "p50": quantiles[:, :, 2].reshape(-1),
            "p75": quantiles[:, :, 3].reshape(-1),
            "p90": quantiles[:, :, 4].reshape(-1),
        }
    )
    return out[mask].reset_index(drop=True)


def add_time_context(predictions: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
    lookup = add_baselines(df)[
        [
            "node_id",
            "time_idx",
            "period",
            "demand_mw",
            "persistence_24h_mw",
            "seasonal_naive_168h_mw",
            "eia_demand_forecast_mw",
        ]
    ].copy()
    lookup = lookup.rename(
        columns={
            "time_idx": "target_time_idx",
            "period": "target_period",
            "demand_mw": "actual_demand_mw",
        }
    )
    out = predictions.merge(lookup, on=["node_id", "target_time_idx"], how="left", validate="many_to_one")
    return out


def mape(actual: pd.Series, predicted: pd.Series) -> float:
    return float(((actual - predicted).abs() / actual.clip(lower=EPS)).mean() * 100)


def mae(actual: pd.Series, predicted: pd.Series) -> float:
    return float((actual - predicted).abs().mean())


def rmse(actual: pd.Series, predicted: pd.Series) -> float:
    return float(((actual - predicted) ** 2).mean() ** 0.5)


def evaluate_one(df: pd.DataFrame, model_name: str, pred_col: str) -> dict[str, float | int | str]:
    usable = df.dropna(subset=["actual_demand_mw", pred_col])
    actual = usable["actual_demand_mw"]
    predicted = usable[pred_col]
    return {
        "model": model_name,
        "n": int(len(usable)),
        "mae_mw": round(mae(actual, predicted), 2),
        "rmse_mw": round(rmse(actual, predicted), 2),
        "mape_pct": round(mape(actual, predicted), 3),
        "bias_mw": round(float((predicted - actual).mean()), 2),
    }


def interval_metrics(df: pd.DataFrame) -> dict[str, float]:
    usable = df.dropna(subset=["actual_demand_mw", "p10", "p25", "p75", "p90"])
    actual = usable["actual_demand_mw"]
    return {
        "p10_p90_coverage_pct": round(float(((actual >= usable["p10"]) & (actual <= usable["p90"])).mean() * 100), 2),
        "p25_p75_coverage_pct": round(float(((actual >= usable["p25"]) & (actual <= usable["p75"])).mean() * 100), 2),
        "mean_p90_p10_width_mw": round(float((usable["p90"] - usable["p10"]).mean()), 2),
    }


def horizon_bucket(lead_hour: int) -> str:
    for start, end, label in HORIZON_BUCKETS:
        if start <= lead_hour <= end:
            return label
    return "other"


def build_metrics(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    candidate_cols = [
        ("tft_p50", "p50"),
        ("persistence_24h", "persistence_24h_mw"),
        ("seasonal_naive_168h", "seasonal_naive_168h_mw"),
        ("eia_day_ahead", "eia_demand_forecast_mw"),
    ]

    rows: list[dict[str, float | int | str]] = []
    groups: list[tuple[str, str, pd.DataFrame]] = [("ALL", "ALL", predictions)]
    groups.extend((str(node_id), "ALL", node_df) for node_id, node_df in predictions.groupby("node_id", sort=True))

    for node_id, horizon, group_df in groups:
        for name, col in candidate_cols:
            if col not in group_df:
                continue
            row = {"node_id": node_id, "horizon_bucket": horizon}
            row.update(evaluate_one(group_df, name, col))
            if name == "tft_p50":
                row.update(interval_metrics(group_df))
            rows.append(row)

    bucket_rows: list[dict[str, float | int | str]] = []
    bucketed = predictions.copy()
    bucketed["horizon_bucket"] = bucketed["lead_hour"].map(horizon_bucket)
    for (node_id, bucket), group_df in bucketed.groupby(["node_id", "horizon_bucket"], sort=True):
        for name, col in candidate_cols:
            row = {"node_id": str(node_id), "horizon_bucket": str(bucket)}
            row.update(evaluate_one(group_df, name, col))
            if name == "tft_p50":
                row.update(interval_metrics(group_df))
            bucket_rows.append(row)
    for bucket, group_df in bucketed.groupby("horizon_bucket", sort=True):
        for name, col in candidate_cols:
            row = {"node_id": "ALL", "horizon_bucket": str(bucket)}
            row.update(evaluate_one(group_df, name, col))
            if name == "tft_p50":
                row.update(interval_metrics(group_df))
            bucket_rows.append(row)

    lead_rows: list[dict[str, float | int | str]] = []
    for lead_hour, group_df in predictions.groupby("lead_hour", sort=True):
        row = {"lead_hour": int(lead_hour)}
        row.update(evaluate_one(group_df, "tft_p50", "p50"))
        row.update(interval_metrics(group_df))
        lead_rows.append(row)

    metrics = pd.DataFrame(rows).sort_values(["node_id", "horizon_bucket", "mape_pct", "model"])
    by_bucket = pd.DataFrame(bucket_rows).sort_values(["node_id", "horizon_bucket", "mape_pct", "model"])
    by_lead = pd.DataFrame(lead_rows).sort_values("lead_hour")
    return metrics, by_bucket, by_lead


def main() -> None:
    args = parse_args()
    metadata = load_metadata(TFT_OUT_DIR)
    checkpoint = resolve_checkpoint(args, metadata)
    train_days = args.train_days if args.train_days is not None else metadata.get("train_days")

    deps = train_tft.require_ml_deps()
    torch = deps["torch"]
    pl = deps["pl"]
    TemporalFusionTransformer = deps["TemporalFusionTransformer"]
    if torch.cuda.is_available():
        torch.set_float32_matmul_precision("medium")
    pl.seed_everything(42, workers=True)

    df = train_tft.load_training_frame(args.data)
    _, validation, validation_start = train_tft.build_datasets(df, deps, fast_dev_run=False, train_days=train_days)
    val_loader = validation.to_dataloader(train=False, batch_size=args.batch_size, num_workers=args.num_workers)

    model = TemporalFusionTransformer.load_from_checkpoint(str(checkpoint))
    prediction = model.predict(
        val_loader,
        mode="quantiles",
        return_x=True,
        return_y=False,
        return_index=True,
        return_decoder_lengths=True,
        trainer_kwargs={
            "accelerator": "auto",
            "devices": "auto",
            "logger": False,
            "enable_progress_bar": True,
            "limit_predict_batches": args.limit_predict_batches,
        },
    )

    predictions = add_time_context(flatten_predictions(prediction), df)
    metrics, by_bucket, by_lead = build_metrics(predictions)

    args.out.mkdir(parents=True, exist_ok=True)
    predictions.to_parquet(args.out / "tft_predictions.parquet", index=False)
    metrics.to_csv(args.out / "tft_eval_metrics.csv", index=False)
    by_bucket.to_csv(args.out / "tft_eval_by_horizon.csv", index=False)
    by_lead.to_csv(args.out / "tft_eval_by_lead_hour.csv", index=False)

    print(f"Checkpoint: {checkpoint}")
    print(f"Validation starts at time_idx={validation_start}")
    print(f"Prediction rows: {len(predictions):,}")
    print(f"Outputs: {args.out}")
    print()
    print("Overall:")
    print(metrics[metrics["node_id"].eq("ALL")].to_string(index=False))
    print()
    print("Horizon buckets, ALL nodes:")
    print(by_bucket[by_bucket["node_id"].eq("ALL")].to_string(index=False))
    print()
    best_baseline = metrics[(metrics["node_id"].eq("ALL")) & (metrics["model"].ne("tft_p50"))].sort_values("mape_pct").head(1)
    tft = metrics[(metrics["node_id"].eq("ALL")) & (metrics["model"].eq("tft_p50"))].head(1)
    if not best_baseline.empty and not tft.empty:
        tft_row = tft.iloc[0]
        base_row = best_baseline.iloc[0]
        delta = float(tft_row["mape_pct"]) - float(base_row["mape_pct"])
        print(
            f"TFT p50 MAPE={tft_row['mape_pct']}% vs best baseline "
            f"{base_row['model']}={base_row['mape_pct']}% (delta {delta:+.3f} pts)"
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
