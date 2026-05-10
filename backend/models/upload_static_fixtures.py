"""One-shot uploader for static demo fixtures to IBM COS.

The Code Engine inference job only writes the 4 live-node JSONs (nodes.json,
forecast/{live-id}.json, live/{live-id}.json). The 16 synthetic nodes and 2
replay events are pre-rendered fixtures that never change. This script
uploads them to COS once so frontend reads in `GRIDCAST_DATA_SOURCE=cos`
mode return real data instead of 404s.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"

SYNTHETIC_NODE_IDS = [
    "miso-indiana-hub", "miso-illinois-hub",
    "spp-north-hub", "spp-south-hub",
    "nyiso-zone-j", "nyiso-zone-a",
    "iso-ne-mass-hub",
    "pjm-western-hub", "pjm-aep-dayton",
    "ercot-north", "ercot-west",
    "caiso-zp26",
    "bpa-pnw", "duke-carolinas", "tva-tennessee", "fpl-florida",
]
REPLAY_IDS = ["texas-2021", "pjm-2023"]


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


def planned_uploads() -> list[tuple[Path, str]]:
    plans: list[tuple[Path, str]] = []
    for node_id in SYNTHETIC_NODE_IDS:
        plans.append((FIXTURES / "forecast" / f"{node_id}.json", f"forecast/{node_id}.json"))
        plans.append((FIXTURES / "live" / f"{node_id}.json", f"live/{node_id}.json"))
    for replay_id in REPLAY_IDS:
        plans.append((FIXTURES / "replay" / f"{replay_id}.json", f"replay/{replay_id}.json"))
    return plans


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-read", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    bucket = require_env("IBM_COS_BUCKET")
    plans = planned_uploads()

    missing = [src for src, _ in plans if not src.exists()]
    if missing:
        print("Missing fixture files:")
        for path in missing:
            print(f"  {path}")
        raise SystemExit(1)

    print(f"Bucket: {bucket}")
    print(f"Uploads planned: {len(plans)}")

    client = None if args.dry_run else cos_client()
    for src, key in plans:
        acl_note = " public-read" if args.public_read else ""
        print(f"{'would upload' if args.dry_run else 'upload'} {key}{acl_note}")
        if client is not None:
            extra_args = {
                "ContentType": "application/json",
                "CacheControl": "no-store",
            }
            if args.public_read:
                extra_args["ACL"] = "public-read"
            client.upload_file(
                Filename=str(src),
                Bucket=bucket,
                Key=key,
                ExtraArgs=extra_args,
            )

    print(f"\n{'Dry run complete' if args.dry_run else 'Upload complete'}: {len(plans)} objects")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
