"""Train a Temporal Fusion Transformer for GridCast demand forecasts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_PATH = ROOT / "backend" / "data" / "processed" / "all_nodes.parquet"
OUT_DIR = ROOT / "backend" / "models" / "out" / "tft"

MAX_ENCODER_LENGTH = 168
MAX_PREDICTION_LENGTH = 240
TEST_DAYS = 60
QUANTILES = [0.10, 0.25, 0.50, 0.75, 0.90]

KNOWN_REAL_FEATURES = [
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
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "doy_sin",
    "doy_cos",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=PROCESSED_PATH, help="Processed all_nodes parquet path.")
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="Output directory for checkpoints and metadata.")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=3e-3)
    parser.add_argument("--hidden-size", type=int, default=32)
    parser.add_argument("--attention-head-size", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--hidden-continuous-size", type=int, default=16)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--train-days", type=int, default=None, help="Limit training history for quick local runs.")
    parser.add_argument("--limit-train-batches", type=float, default=None, help="Lightning limit_train_batches.")
    parser.add_argument("--limit-val-batches", type=float, default=None, help="Lightning limit_val_batches.")
    parser.add_argument("--fast-dev-run", action="store_true", help="Run one tiny train/val step to test plumbing.")
    return parser.parse_args()


def require_ml_deps() -> dict[str, Any]:
    try:
        import torch
        import lightning.pytorch as pl
        from lightning.pytorch.callbacks import EarlyStopping, LearningRateMonitor, ModelCheckpoint
        from lightning.pytorch.loggers import CSVLogger
        from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
        from pytorch_forecasting.data import GroupNormalizer
        from pytorch_forecasting.metrics import QuantileLoss
    except ImportError as exc:
        raise SystemExit(
            "Missing ML dependencies. Install them with:\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install -r backend\\requirements-ml.txt"
        ) from exc

    return {
        "torch": torch,
        "pl": pl,
        "EarlyStopping": EarlyStopping,
        "LearningRateMonitor": LearningRateMonitor,
        "ModelCheckpoint": ModelCheckpoint,
        "CSVLogger": CSVLogger,
        "TemporalFusionTransformer": TemporalFusionTransformer,
        "TimeSeriesDataSet": TimeSeriesDataSet,
        "GroupNormalizer": GroupNormalizer,
        "QuantileLoss": QuantileLoss,
    }


def load_training_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run backend/data/build_features.py first.")

    df = pd.read_parquet(path)
    df["period"] = pd.to_datetime(df["period"], utc=True)
    df = df.sort_values(["node_id", "period"]).reset_index(drop=True)

    start = df["period"].min()
    df["time_idx"] = ((df["period"] - start).dt.total_seconds() // 3600).astype("int64")
    df["node_id"] = df["node_id"].astype(str)
    df["demand_mw"] = pd.to_numeric(df["demand_mw"], errors="coerce").astype("float32")

    for col in KNOWN_REAL_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float32")

    required = ["node_id", "time_idx", "demand_mw", *KNOWN_REAL_FEATURES]
    df = df.dropna(subset=required).reset_index(drop=True)
    return df


def build_datasets(
    df: pd.DataFrame,
    deps: dict[str, Any],
    fast_dev_run: bool,
    train_days: int | None,
) -> tuple[Any, Any, int]:
    TimeSeriesDataSet = deps["TimeSeriesDataSet"]
    GroupNormalizer = deps["GroupNormalizer"]

    validation_start = int(df["time_idx"].max() - TEST_DAYS * 24)
    training_df = df[df["time_idx"] < validation_start].copy()

    if train_days is not None:
        min_idx = max(int(training_df["time_idx"].max()) - train_days * 24, int(training_df["time_idx"].min()))
        training_df = training_df[training_df["time_idx"] >= min_idx].copy()

    if fast_dev_run:
        min_idx = max(int(training_df["time_idx"].max()) - 45 * 24, int(training_df["time_idx"].min()))
        training_df = training_df[training_df["time_idx"] >= min_idx].copy()

    dataset_kwargs = {
        "time_idx": "time_idx",
        "target": "demand_mw",
        "group_ids": ["node_id"],
        "max_encoder_length": MAX_ENCODER_LENGTH,
        "max_prediction_length": MAX_PREDICTION_LENGTH,
        "min_encoder_length": MAX_ENCODER_LENGTH // 2,
        "min_prediction_length": 24,
        "static_categoricals": ["node_id"],
        "time_varying_known_reals": ["time_idx", *KNOWN_REAL_FEATURES],
        "time_varying_unknown_reals": ["demand_mw"],
        "target_normalizer": GroupNormalizer(groups=["node_id"], transformation="softplus"),
        "add_relative_time_idx": True,
        "add_target_scales": True,
        "add_encoder_length": True,
        "allow_missing_timesteps": True,
    }

    training = TimeSeriesDataSet(training_df, **dataset_kwargs)
    validation = TimeSeriesDataSet.from_dataset(
        training,
        df,
        min_prediction_idx=validation_start,
        stop_randomization=True,
    )
    return training, validation, validation_start


def main() -> None:
    args = parse_args()
    deps = require_ml_deps()
    torch = deps["torch"]
    pl = deps["pl"]
    TemporalFusionTransformer = deps["TemporalFusionTransformer"]
    QuantileLoss = deps["QuantileLoss"]
    EarlyStopping = deps["EarlyStopping"]
    LearningRateMonitor = deps["LearningRateMonitor"]
    ModelCheckpoint = deps["ModelCheckpoint"]
    CSVLogger = deps["CSVLogger"]

    args.out.mkdir(parents=True, exist_ok=True)
    if torch.cuda.is_available():
        torch.set_float32_matmul_precision("medium")
    pl.seed_everything(42, workers=True)

    df = load_training_frame(args.data)
    training, validation, validation_start = build_datasets(df, deps, args.fast_dev_run, args.train_days)
    train_loader = training.to_dataloader(train=True, batch_size=args.batch_size, num_workers=args.num_workers)
    val_loader = validation.to_dataloader(train=False, batch_size=args.batch_size, num_workers=args.num_workers)

    model = TemporalFusionTransformer.from_dataset(
        training,
        learning_rate=args.learning_rate,
        hidden_size=args.hidden_size,
        attention_head_size=args.attention_head_size,
        dropout=args.dropout,
        hidden_continuous_size=args.hidden_continuous_size,
        loss=QuantileLoss(quantiles=QUANTILES),
        optimizer="adam",
        reduce_on_plateau_patience=3,
    )

    checkpoint = None
    callbacks = []
    if not args.fast_dev_run:
        checkpoint = ModelCheckpoint(
            dirpath=args.out / "checkpoints",
            filename="gridcast-tft-{epoch:02d}-{val_loss:.4f}",
            monitor="val_loss",
            mode="min",
            save_top_k=1,
        )
        callbacks.append(checkpoint)
        callbacks.append(EarlyStopping(monitor="val_loss", patience=5, mode="min"))
        callbacks.append(LearningRateMonitor(logging_interval="epoch"))
    logger = CSVLogger(save_dir=args.out, name="logs")

    trainer = pl.Trainer(
        max_epochs=args.epochs,
        accelerator="auto",
        devices="auto",
        gradient_clip_val=0.1,
        callbacks=callbacks,
        logger=logger,
        fast_dev_run=args.fast_dev_run,
        enable_checkpointing=not args.fast_dev_run,
        limit_train_batches=args.limit_train_batches,
        limit_val_batches=args.limit_val_batches,
        log_every_n_steps=10,
    )

    trainer.fit(model, train_dataloaders=train_loader, val_dataloaders=val_loader)

    metadata = {
        "data": str(args.data),
        "validation_start_time_idx": validation_start,
        "max_encoder_length": MAX_ENCODER_LENGTH,
        "max_prediction_length": MAX_PREDICTION_LENGTH,
        "quantiles": QUANTILES,
        "known_real_features": KNOWN_REAL_FEATURES,
        "train_days": args.train_days,
        "limit_train_batches": args.limit_train_batches,
        "limit_val_batches": args.limit_val_batches,
        "best_model_path": checkpoint.best_model_path if checkpoint is not None else None,
    }
    (args.out / "training_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    print(f"Training windows: {len(training):,}")
    print(f"Validation windows: {len(validation):,}")
    print(f"Validation starts at time_idx={validation_start}")
    print(f"Outputs: {args.out}")
    if checkpoint is not None and checkpoint.best_model_path:
        print(f"Best checkpoint: {checkpoint.best_model_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
