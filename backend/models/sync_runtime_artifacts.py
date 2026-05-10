"""Sync runtime artifacts between local disk and IBM COS.

These artifacts are intentionally not committed to Git:
- trained TFT checkpoint
- calibration JSON
- processed feature parquet
- weather forecast parquet files

The Code Engine job downloads them before running inference.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "backend" / "data" / "raw"
PROCESSED_DIR = ROOT / "backend" / "data" / "processed"
MODEL_OUT_DIR = ROOT / "backend" / "models" / "out"

LOCAL_CHECKPOINT = MODEL_OUT_DIR / "tft" / "checkpoints" / "checkpoint.ckpt"
LOCAL_CALIBRATION = MODEL_OUT_DIR / "tft_calibration.json"
LOCAL_FEATURES = PROCESSED_DIR / "all_nodes.parquet"
LOCAL_WEATHER_FORECASTS = [
    RAW_DIR / "weather_forecast_dominion_hub.parquet",
    RAW_DIR / "weather_forecast_caiso_sp15.parquet",
    RAW_DIR / "weather_forecast_caiso_np15.parquet",
    RAW_DIR / "weather_forecast_ercot_houston.parquet",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("direction", choices=["upload", "download"])
    parser.add_argument("--prefix", default=os.getenv("GRIDCAST_RUNTIME_ARTIFACT_PREFIX", "artifacts/current"))
    parser.add_argument("--checkpoint", type=Path, default=None, help="Checkpoint to upload. Defaults to training metadata.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def cos_client() -> object:
    try:
        import ibm_boto3
        from ibm_botocore.client import Config
    except ImportError as exc:
        raise SystemExit(
            "Missing IBM COS dependency. Install it with:\n"
            "  .\\.venv\\Scripts\\python.exe -m pip install -r backend\\requirements.txt"
        ) from exc

    return ibm_boto3.client(
        "s3",
        ibm_api_key_id=require_env("IBM_COS_API_KEY"),
        ibm_service_instance_id=require_env("IBM_COS_RESOURCE_INSTANCE_ID"),
        config=Config(signature_version="oauth"),
        endpoint_url=require_env("IBM_COS_ENDPOINT"),
    )


def object_key(prefix: str, key: str) -> str:
    return f"{prefix.strip('/')}/{key.lstrip('/')}"


def best_checkpoint() -> Path:
    metadata_path = MODEL_OUT_DIR / "tft" / "training_metadata.json"
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("best_model_path"):
            path = Path(metadata["best_model_path"])
            if path.exists():
                return path

    checkpoints = sorted((MODEL_OUT_DIR / "tft" / "checkpoints").glob("*.ckpt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not checkpoints:
        raise FileNotFoundError("No checkpoint found. Run backend/models/train_tft.py first.")
    return checkpoints[0]


def artifact_map(checkpoint: Path | None) -> list[tuple[Path, str]]:
    ckpt = checkpoint or best_checkpoint()
    artifacts = [
        (ckpt, "model/checkpoint.ckpt"),
        (LOCAL_CALIBRATION, "model/tft_calibration.json"),
        (LOCAL_FEATURES, "data/processed/all_nodes.parquet"),
    ]
    artifacts.extend((path, f"data/raw/{path.name}") for path in LOCAL_WEATHER_FORECASTS)
    return artifacts


def upload(args: argparse.Namespace) -> None:
    bucket = require_env("IBM_COS_BUCKET")
    client = None if args.dry_run else cos_client()

    for local_path, key in artifact_map(args.checkpoint):
        if not local_path.exists():
            raise FileNotFoundError(f"Missing runtime artifact: {local_path}")
        cos_key = object_key(args.prefix, key)
        print(f"{'would upload' if args.dry_run else 'upload'} {local_path} -> {cos_key}")
        if client is not None:
            client.upload_file(str(local_path), bucket, cos_key)


def download(args: argparse.Namespace) -> None:
    bucket = require_env("IBM_COS_BUCKET")
    client = None if args.dry_run else cos_client()
    downloads = [
        (LOCAL_CHECKPOINT, "model/checkpoint.ckpt"),
        (LOCAL_CALIBRATION, "model/tft_calibration.json"),
        (LOCAL_FEATURES, "data/processed/all_nodes.parquet"),
        *[(path, f"data/raw/{path.name}") for path in LOCAL_WEATHER_FORECASTS],
    ]

    for local_path, key in downloads:
        cos_key = object_key(args.prefix, key)
        print(f"{'would download' if args.dry_run else 'download'} {cos_key} -> {local_path}")
        if client is not None:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(bucket, cos_key, str(local_path))


def main() -> None:
    args = parse_args()
    load_dotenv(ROOT / ".env")

    if args.direction == "upload":
        upload(args)
    else:
        download(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
