"""Upload exported GridCast JSON payloads to IBM Cloud Object Storage."""
from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PAYLOAD_DIR = ROOT / "backend" / "models" / "out" / "cos_payload"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload-dir", type=Path, default=DEFAULT_PAYLOAD_DIR)
    parser.add_argument("--prefix", default="", help="Optional COS key prefix, e.g. runs/2026-05-10T0400Z")
    parser.add_argument("--public-read", action="store_true", help="Set object ACL to public-read for COS_BASE_URL reads.")
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
            "  .\\.venv\\Scripts\\python.exe -m pip install -r backend\\requirements-base.txt"
        ) from exc

    return ibm_boto3.client(
        "s3",
        ibm_api_key_id=require_env("IBM_COS_API_KEY"),
        ibm_service_instance_id=require_env("IBM_COS_RESOURCE_INSTANCE_ID"),
        config=Config(signature_version="oauth"),
        endpoint_url=require_env("IBM_COS_ENDPOINT"),
    )


def iter_payloads(payload_dir: Path) -> list[Path]:
    if not payload_dir.exists():
        raise FileNotFoundError(f"Missing payload dir: {payload_dir}. Run backend/models/export_forecasts.py first.")
    return sorted(path for path in payload_dir.rglob("*.json") if path.is_file())


def object_key(payload_dir: Path, path: Path, prefix: str) -> str:
    key = path.relative_to(payload_dir).as_posix()
    clean_prefix = prefix.strip("/")
    return f"{clean_prefix}/{key}" if clean_prefix else key


def main() -> None:
    args = parse_args()
    load_dotenv(ROOT / ".env")

    bucket = require_env("IBM_COS_BUCKET")
    paths = iter_payloads(args.payload_dir)
    if not paths:
        raise RuntimeError(f"No JSON payloads found under {args.payload_dir}")

    print(f"Bucket: {bucket}")
    print(f"Payload dir: {args.payload_dir}")
    print(f"Prefix: {args.prefix or '(bucket root)'}")
    print()

    client = None if args.dry_run else cos_client()
    for path in paths:
        key = object_key(args.payload_dir, path, args.prefix)
        content_type = mimetypes.guess_type(path.name)[0] or "application/json"
        acl_note = " public-read" if args.public_read else ""
        print(f"{'would upload' if args.dry_run else 'upload'} {key}{acl_note}")
        if client is not None:
            extra_args = {
                "ContentType": content_type,
                "CacheControl": "no-store",
            }
            if args.public_read:
                extra_args["ACL"] = "public-read"
            client.upload_file(
                Filename=str(path),
                Bucket=bucket,
                Key=key,
                ExtraArgs=extra_args,
            )

    print(f"\n{'Dry run complete' if args.dry_run else 'Upload complete'}: {len(paths)} objects")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
