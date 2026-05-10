"""One-shot GridCast inference job entrypoint for IBM Code Engine."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def run(args: list[str]) -> None:
    print(f"\n$ {' '.join(args)}", flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    load_dotenv(ROOT / ".env")

    payload_dir = os.getenv("GRIDCAST_COS_PAYLOAD_DIR", str(ROOT / "backend" / "models" / "out" / "cos_payload"))
    artifact_prefix = os.getenv("GRIDCAST_RUNTIME_ARTIFACT_PREFIX", "artifacts/current")
    train_days = os.getenv("GRIDCAST_TFT_TRAIN_DAYS", "365")
    public_read = env_bool("GRIDCAST_COS_PUBLIC_READ", True)
    download_artifacts = env_bool("GRIDCAST_DOWNLOAD_RUNTIME_ARTIFACTS", True)

    checkpoint = ROOT / "backend" / "models" / "out" / "tft" / "checkpoints" / "checkpoint.ckpt"
    calibration = ROOT / "backend" / "models" / "out" / "tft_calibration.json"
    features = ROOT / "backend" / "data" / "processed" / "all_nodes.parquet"

    if download_artifacts:
        run(
            [
                PYTHON,
                "backend/models/sync_runtime_artifacts.py",
                "download",
                "--prefix",
                artifact_prefix,
            ]
        )

    run(
        [
            PYTHON,
            "backend/models/export_forecasts.py",
            "--source",
            "cos",
            "--checkpoint",
            str(checkpoint),
            "--calibration",
            str(calibration),
            "--data",
            str(features),
            "--out",
            payload_dir,
            "--train-days",
            train_days,
        ]
    )

    upload_command = [
        PYTHON,
        "backend/models/upload_cos.py",
        "--payload-dir",
        payload_dir,
    ]
    if public_read:
        upload_command.append("--public-read")
    run(upload_command)

    print("\nGridCast inference publish complete.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"\nCommand failed with exit code {exc.returncode}: {exc.cmd}", file=sys.stderr)
        sys.exit(exc.returncode)
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
