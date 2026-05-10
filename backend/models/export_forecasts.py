"""Export trained TFT forecasts to the GridCast frontend JSON contract."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import train_tft

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "backend" / "data" / "raw"
PROCESSED_PATH = ROOT / "backend" / "data" / "processed" / "all_nodes.parquet"
MODEL_OUT_DIR = ROOT / "backend" / "models" / "out"
TFT_OUT_DIR = MODEL_OUT_DIR / "tft"
DEFAULT_EXPORT_DIR = MODEL_OUT_DIR / "cos_payload"

HORIZON_HOURS = 240
ENCODER_HOURS = 168
ENSEMBLE_MEMBERS = 16
QUANTILE_LEVELS = [0.1, 0.25, 0.5, 0.75, 0.9]
QUANTILE_COLS = ["p10", "p25", "p50", "p75", "p90"]

NODE_CONFIG = {
    "dominion-hub": {
        "name": "Dominion Hub",
        "iso": "PJM",
        "state": "VA",
        "ba_code": "PJM",
        "lat": 38.9,
        "lon": -77.0,
        "raw_weather_id": "dominion_hub",
        "forecast_weather_path": "weather_forecast_dominion_hub.parquet",
        "stress_threshold_demand_mw": 14500.0,
        "data_centers": [
            ("aws-ashburn", "AWS Ashburn Campus", "AWS", 1200.0),
            ("azure-east", "Microsoft Azure East", "Microsoft", 800.0),
            ("google-loudoun", "Google Loudoun", "Google", 650.0),
        ],
    },
    "caiso-sp15": {
        "name": "CAISO SP15",
        "iso": "CAISO",
        "state": "CA",
        "ba_code": "CAISO",
        "lat": 34.05,
        "lon": -118.25,
        "raw_weather_id": "caiso_sp15",
        "forecast_weather_path": "weather_forecast_caiso_sp15.parquet",
        "stress_threshold_demand_mw": 23000.0,
        "data_centers": [
            ("azure-west", "Microsoft Azure West", "Microsoft", 500.0),
            ("google-west-la", "Google West-LA", "Google", 400.0),
            ("meta-sandstone", "Meta Sandstone", "Meta", 350.0),
        ],
    },
    "caiso-np15": {
        "name": "CAISO NP15",
        "iso": "CAISO",
        "state": "CA",
        "ba_code": "CAISO",
        "lat": 37.77,
        "lon": -122.42,
        "raw_weather_id": "caiso_np15",
        "forecast_weather_path": "weather_forecast_caiso_np15.parquet",
        "stress_threshold_demand_mw": 14000.0,
        "data_centers": [
            ("google-bay-west", "Google Bay-West", "Google", 600.0),
            ("meta-mpk", "Meta MPK Campus", "Meta", 500.0),
            ("nvidia-santa-clara", "NVIDIA Santa Clara", "NVIDIA", 300.0),
        ],
    },
    "ercot-houston": {
        "name": "ERCOT Houston",
        "iso": "ERCOT",
        "state": "TX",
        "ba_code": "ERCOT",
        "lat": 29.76,
        "lon": -95.37,
        "raw_weather_id": "ercot_houston",
        "forecast_weather_path": "weather_forecast_ercot_houston.parquet",
        "stress_threshold_demand_mw": 16000.0,
        "data_centers": [
            ("azure-tx", "Microsoft Azure TX", "Microsoft", 700.0),
            ("aws-tx-east", "AWS TX-East", "AWS", 550.0),
            ("google-south-tx", "Google South-TX", "Google", 450.0),
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=PROCESSED_PATH)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--calibration", type=Path, default=MODEL_OUT_DIR / "tft_calibration.json")
    parser.add_argument("--out", type=Path, default=DEFAULT_EXPORT_DIR)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--train-days", type=int, default=None, help="Override training history window for dataset rebuild.")
    parser.add_argument("--source", choices=["fixtures", "cos"], default="cos")
    parser.add_argument("--no-calibration", action="store_true")
    return parser.parse_args()


def iso_z(value: pd.Timestamp | datetime) -> str:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def tier(capacity_mw: float) -> str:
    if capacity_mw >= 700:
        return "large"
    if capacity_mw >= 400:
        return "medium"
    return "small"


def load_training_metadata() -> dict[str, Any]:
    path = TFT_OUT_DIR / "training_metadata.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def resolve_checkpoint(args: argparse.Namespace, metadata: dict[str, Any]) -> Path:
    if args.checkpoint is not None:
        checkpoint = args.checkpoint
    elif metadata.get("best_model_path"):
        checkpoint = Path(metadata["best_model_path"])
    else:
        checkpoints = sorted((TFT_OUT_DIR / "checkpoints").glob("*.ckpt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not checkpoints:
            raise FileNotFoundError("No TFT checkpoint found. Run backend/models/train_tft.py first.")
        checkpoint = checkpoints[0]
    if not checkpoint.exists():
        raise FileNotFoundError(f"Missing checkpoint: {checkpoint}")
    return checkpoint


def load_calibration(path: Path, enabled: bool) -> dict[tuple[str, str], dict[str, float]]:
    if not enabled:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Missing calibration artifact: {path}. Run backend/models/calibrate_tft.py first.")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        (group["node_id"], group["horizon_bucket"]): {key: float(value) for key, value in group["corrections_mw"].items()}
        for group in raw["groups"]
    }


def load_processed(path: Path) -> pd.DataFrame:
    df = train_tft.load_training_frame(path)
    source = pd.read_parquet(path)
    source["period"] = pd.to_datetime(source["period"], utc=True)
    keep_cols = ["node_id", "period", "demand_mw", "eia_demand_forecast_mw", *train_tft.KNOWN_REAL_FEATURES]
    return source[keep_cols].merge(df[["node_id", "period", "time_idx"]], on=["node_id", "period"], how="inner")


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
    out["hour_sin"] = np.sin(2 * math.pi * hour / 24)
    out["hour_cos"] = np.cos(2 * math.pi * hour / 24)
    out["dow_sin"] = np.sin(2 * math.pi * day_of_week / 7)
    out["dow_cos"] = np.cos(2 * math.pi * day_of_week / 7)
    out["doy_sin"] = np.sin(2 * math.pi * day_of_year / 366)
    out["doy_cos"] = np.cos(2 * math.pi * day_of_year / 366)
    return out


def load_weather_forecast(path: Path) -> tuple[pd.DataFrame, list[list[float]], str]:
    df = pd.read_parquet(path)
    df["period"] = pd.to_datetime(df["period"], utc=True)
    fetched_at = str(df["fetched_at"].iloc[0])
    member_mean = df.groupby("period", as_index=False)[train_tft.KNOWN_REAL_FEATURES[:10]].mean()

    members = []
    for member, member_df in df[df["member"].lt(ENSEMBLE_MEMBERS)].groupby("member", sort=True):
        values = member_df.sort_values("period")["temperature_2m"].astype(float).head(HORIZON_HOURS).round(2).tolist()
        if len(values) == HORIZON_HOURS:
            members.append(values)
    if len(members) != ENSEMBLE_MEMBERS:
        raise ValueError(f"Expected {ENSEMBLE_MEMBERS} weather members in {path}, got {len(members)}")
    return member_mean, members, fetched_at


def regularize_history(node_df: pd.DataFrame, global_start: pd.Timestamp) -> pd.DataFrame:
    """Return a continuous 168-hour history ending at the latest observed row.

    EIA occasionally leaves short holes in recent hourly data. The frontend schema
    intentionally requires contiguous history so charts do not break. We fill
    missing hours here at the publication boundary rather than weakening the UI
    contract.
    """
    latest = node_df["period"].max()
    history_periods = pd.date_range(
        latest - pd.Timedelta(hours=ENCODER_HOURS - 1),
        periods=ENCODER_HOURS,
        freq="h",
        tz="UTC",
    )
    history = node_df.drop_duplicates("period").set_index("period").reindex(history_periods)
    history.index.name = "period"
    history["node_id"] = history["node_id"].ffill().bfill()
    history["eia_demand_forecast_mw"] = history["eia_demand_forecast_mw"].ffill().bfill()
    history["demand_mw"] = history["demand_mw"].interpolate(method="time").ffill().bfill()
    for col in train_tft.KNOWN_REAL_FEATURES:
        history[col] = history[col].interpolate(method="time").ffill().bfill()
    history = add_calendar_features(history.reset_index())
    history["time_idx"] = ((history["period"] - global_start).dt.total_seconds() // 3600).astype("int64")
    return history


def build_prediction_frame(processed: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    frames = []
    context: dict[str, Any] = {}
    global_start = processed["period"].min()

    for node_id, cfg in NODE_CONFIG.items():
        node_df = processed[processed["node_id"].eq(node_id)].sort_values("period").copy()
        if len(node_df) < ENCODER_HOURS:
            raise ValueError(f"{node_id} has fewer than {ENCODER_HOURS} historical rows")
        history = regularize_history(node_df, global_start)

        weather_forecast, ensemble_members, fetched_at = load_weather_forecast(RAW_DIR / str(cfg["forecast_weather_path"]))
        forecast_start = node_df["period"].max() + pd.Timedelta(hours=1)
        forecast_periods = pd.date_range(forecast_start, periods=HORIZON_HOURS, freq="h", tz="UTC")

        future_weather = weather_forecast.set_index("period").reindex(forecast_periods)
        historical_weather = node_df.set_index("period")[train_tft.KNOWN_REAL_FEATURES[:10]]
        future_weather = future_weather.combine_first(historical_weather.reindex(forecast_periods))
        future_weather = future_weather.ffill().bfill()

        future = future_weather.reset_index(names="period")
        future.insert(0, "node_id", node_id)
        future["demand_mw"] = float(node_df["demand_mw"].iloc[-1])
        future["eia_demand_forecast_mw"] = np.nan
        future = add_calendar_features(future)
        future["time_idx"] = ((future["period"] - global_start).dt.total_seconds() // 3600).astype("int64")

        combined = pd.concat([history, future], ignore_index=True, sort=False)
        frames.append(combined)
        context[node_id] = {
            "forecast_start": forecast_start,
            "forecast_periods": forecast_periods,
            "history": history,
            "ensemble_members": ensemble_members,
            "weather_fetched_at": fetched_at,
            "last_live": node_df.iloc[-1],
        }

    prediction_df = pd.concat(frames, ignore_index=True)
    prediction_df["node_id"] = prediction_df["node_id"].astype(str)
    for col in ["demand_mw", *train_tft.KNOWN_REAL_FEATURES]:
        prediction_df[col] = pd.to_numeric(prediction_df[col], errors="coerce").astype("float32")
    prediction_df = prediction_df.dropna(subset=["node_id", "time_idx", "demand_mw", *train_tft.KNOWN_REAL_FEATURES])
    return prediction_df, context


def _force_module_to_cpu(module: Any, torch_mod: Any) -> None:
    """Move a module's tensor state to CPU without going through nn.Module._apply.

    Saved torchmetrics modules in pytorch-forecasting checkpoint hyperparameters
    can carry cuda-bound buffers and a cached _device attribute. Calling .to('cpu')
    or .cpu() on them triggers Metric._apply, which evaluates self.device and
    allocates torch.zeros(1, device=self.device) — that crashes on CPU-only torch
    when self.device is cuda. We fix this by mutating _parameters / _buffers
    dicts and any cached device attributes directly, then recursing into children.
    """
    Tensor = torch_mod.Tensor
    Parameter = torch_mod.nn.Parameter
    cpu = torch_mod.device("cpu")

    for name in list(module._parameters):
        param = module._parameters[name]
        if param is not None and param.device.type != "cpu":
            module._parameters[name] = Parameter(
                param.data.to(cpu), requires_grad=param.requires_grad
            )

    for name in list(module._buffers):
        buf = module._buffers[name]
        if buf is not None and buf.device.type != "cpu":
            module._buffers[name] = buf.to(cpu)

    for key, value in list(module.__dict__.items()):
        if isinstance(value, torch_mod.device) and value.type != "cpu":
            module.__dict__[key] = cpu
        elif isinstance(value, str) and "cuda" in value:
            module.__dict__[key] = "cpu"
        elif isinstance(value, Tensor) and value.device.type != "cpu":
            module.__dict__[key] = value.to(cpu)
        elif isinstance(value, list):
            module.__dict__[key] = [
                v.to(cpu) if isinstance(v, Tensor) and v.device.type != "cpu" else v
                for v in value
            ]

    for child in module.children():
        _force_module_to_cpu(child, torch_mod)


def _walk_force_cpu(obj: Any, torch_mod: Any) -> None:
    if isinstance(obj, torch_mod.nn.Module):
        _force_module_to_cpu(obj, torch_mod)
    elif isinstance(obj, dict):
        for value in obj.values():
            _walk_force_cpu(value, torch_mod)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            _walk_force_cpu(value, torch_mod)


def _make_cpu_safe_checkpoint(checkpoint: Path, torch_mod: Any) -> Path:
    """Surgically rewrite a GPU-trained checkpoint so it loads cleanly on CPU-only torch.

    Returns a path to a parallel '.cpu.ckpt' file with all cuda tensors and
    cached device attributes flipped to CPU. Idempotent: if the .cpu.ckpt is
    newer than the source, returns the cached one.
    """
    cleaned = checkpoint.with_suffix(".cpu.ckpt")
    if cleaned.exists() and cleaned.stat().st_mtime >= checkpoint.stat().st_mtime:
        return cleaned

    raw = torch_mod.load(str(checkpoint), map_location="cpu", weights_only=False)
    _walk_force_cpu(raw, torch_mod)
    torch_mod.save(raw, str(cleaned))
    return cleaned


def horizon_bucket(lead_hour: int) -> str:
    if lead_hour <= 24:
        return "001-024h"
    if lead_hour <= 72:
        return "025-072h"
    if lead_hour <= 168:
        return "073-168h"
    return "169-240h"


def apply_calibration(node_id: str, quantiles: np.ndarray, corrections: dict[tuple[str, str], dict[str, float]]) -> np.ndarray:
    if not corrections:
        return np.maximum.accumulate(quantiles, axis=1)

    calibrated = quantiles.copy()
    for i in range(calibrated.shape[0]):
        bucket = horizon_bucket(i + 1)
        group = corrections.get((node_id, bucket))
        if not group:
            continue
        calibrated[i, :] = calibrated[i, :] + np.array([group[col] for col in QUANTILE_COLS])
    return np.maximum.accumulate(calibrated, axis=1)


def stress_from_quantiles(row: np.ndarray, threshold: float) -> float:
    p10, p25, p50, p75, p90 = [float(x) for x in row]
    if threshold <= p10:
        return 1.0
    points = [(p10, 0.1), (p25, 0.25), (p50, 0.5), (p75, 0.75), (p90, 0.9)]
    for (low_value, low_p), (high_value, high_p) in zip(points, points[1:]):
        if threshold <= high_value:
            if high_value == low_value:
                return max(0.0, min(1.0, 1.0 - high_p))
            cdf = low_p + (high_p - low_p) * (threshold - low_value) / (high_value - low_value)
            return max(0.0, min(1.0, 1.0 - cdf))
    if p90 <= p75:
        return 0.0
    p99 = p90 + ((p90 - p75) / (0.9 - 0.75)) * (0.99 - 0.9)
    if threshold >= p99:
        return 0.0
    cdf = 0.9 + ((0.99 - 0.9) * (threshold - p90)) / (p99 - p90)
    return max(0.0, min(1.0, 1.0 - cdf))


def allocation_pct(stress_fraction: float) -> int:
    return int(round((1 - stress_fraction) * 100))


def build_data_centers(node_id: str, allocation: dict[str, float]) -> list[dict[str, Any]]:
    centers = []
    for center_id, name, operator, capacity in NODE_CONFIG[node_id]["data_centers"]:
        centers.append(
            {
                "id": center_id,
                "name": name,
                "operator": operator,
                "tier": tier(float(capacity)),
                "capacity_mw": capacity,
                "committed_draw_mw": {
                    "p10": round(capacity * allocation["pct_p10"] / 100, 2),
                    "p50": round(capacity * allocation["pct_p50"] / 100, 2),
                    "p90": round(capacity * allocation["pct"] / 100, 2),
                },
            }
        )
    return centers


def build_payloads(
    prediction: Any,
    context: dict[str, Any],
    corrections: dict[tuple[str, str], dict[str, float]],
    source: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    output = prediction.output.detach().cpu().numpy()
    index = prediction.index.reset_index(drop=True)
    issued_at = iso_z(datetime.now(UTC))

    nodes = []
    forecasts = {}
    lives = {}

    for i, row in index.iterrows():
        node_id = str(row["node_id"])
        cfg = NODE_CONFIG[node_id]
        quantiles = apply_calibration(node_id, output[i], corrections)
        threshold = float(cfg["stress_threshold_demand_mw"])
        stress_probs = [stress_from_quantiles(quantiles[j], threshold) for j in range(HORIZON_HOURS)]
        p90_stress_fraction = float(np.quantile(stress_probs, 0.9))
        p50_stress_fraction = float(np.median(stress_probs))
        p10_stress_fraction = float(np.quantile(stress_probs, 0.1))
        allocation = {
            "pct": allocation_pct(p90_stress_fraction),
            "pct_p50": allocation_pct(p50_stress_fraction),
            "pct_p10": allocation_pct(p10_stress_fraction),
            "p90_stress_fraction": round(float(p90_stress_fraction), 4),
        }
        allocation["pct_p50"] = max(allocation["pct"], allocation["pct_p50"])
        allocation["pct_p10"] = max(allocation["pct_p50"], allocation["pct_p10"])

        node_context = context[node_id]
        forecast_timestamps = [iso_z(ts) for ts in node_context["forecast_periods"]]
        history = node_context["history"]
        last_live = node_context["last_live"]
        demand = float(last_live["demand_mw"])
        demand_forecast = float(last_live["eia_demand_forecast_mw"]) if pd.notna(last_live["eia_demand_forecast_mw"]) else demand

        forecast_payload = {
            "node_id": node_id,
            "schema_version": 1,
            "issued_at": issued_at,
            "published_at": issued_at,
            "source": source,
            "horizon_hours": HORIZON_HOURS,
            "encoder_hours": ENCODER_HOURS,
            "quantile_levels": QUANTILE_LEVELS,
            "stress_threshold_demand_mw": threshold,
            "history": {
                "timestamps": [iso_z(ts) for ts in history["period"]],
                "demand_mw": [round(float(v), 2) for v in history["demand_mw"]],
            },
            "forecast": {
                "target": "demand_mw",
                "unit": "MW",
                "timestamps": forecast_timestamps,
                "p10": [round(float(v), 2) for v in quantiles[:, 0]],
                "p25": [round(float(v), 2) for v in quantiles[:, 1]],
                "p50": [round(float(v), 2) for v in quantiles[:, 2]],
                "p75": [round(float(v), 2) for v in quantiles[:, 3]],
                "p90": [round(float(v), 2) for v in quantiles[:, 4]],
            },
            "allocation": allocation,
            "stress_timeline": [
                {"hour_offset": hour, "stress_probability": round(float(prob), 4)}
                for hour, prob in enumerate(stress_probs)
            ],
            "ensemble_spread": {
                "variable": "temperature_2m",
                "unit": "celsius",
                "timestamps": forecast_timestamps,
                "members": node_context["ensemble_members"],
            },
            "data_centers": build_data_centers(node_id, allocation),
        }

        live_payload = {
            "node_id": node_id,
            "schema_version": 1,
            "fetched_at": issued_at,
            "source": source,
            "eia": {
                "demand_mw": round(demand, 2),
                "demand_forecast_mw": round(demand_forecast, 2),
                "demand_deviation_pct": round(((demand - demand_forecast) / max(abs(demand_forecast), 1e-9)) * 100, 3),
            },
            "weather": {
                "temperature_2m_c": round(float(last_live["temperature_2m"]), 2),
                "wind_speed_10m_ms": round(float(last_live["wind_speed_10m"]), 2),
                "ensemble_member_count": ENSEMBLE_MEMBERS,
            },
        }

        node_payload = {
            "id": node_id,
            "name": cfg["name"],
            "iso": cfg["iso"],
            "state": cfg["state"],
            "ba_code": cfg["ba_code"],
            "lat": cfg["lat"],
            "lon": cfg["lon"],
            "stress_probability": round(float(p90_stress_fraction), 4),
            "allocation_pct": allocation["pct"],
            "is_live": True,
        }

        forecasts[node_id] = forecast_payload
        lives[node_id] = live_payload
        nodes.append(node_payload)

    return nodes, forecasts, lives


def merge_synthetic_nodes(nodes: list[dict[str, Any]], source: str, issued_at: str) -> dict[str, Any]:
    fixture_path = ROOT / "fixtures" / "nodes.json"
    if fixture_path.exists():
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        synthetic = [node for node in fixture.get("nodes", []) if not node.get("is_live")]
    else:
        synthetic = []
    return {
        "schema_version": 1,
        "issued_at": issued_at,
        "published_at": issued_at,
        "source": source,
        "nodes": [*nodes, *synthetic],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    metadata = load_training_metadata()
    checkpoint = resolve_checkpoint(args, metadata)
    train_days = args.train_days if args.train_days is not None else metadata.get("train_days")
    corrections = load_calibration(args.calibration, enabled=not args.no_calibration)

    deps = train_tft.require_ml_deps()
    torch = deps["torch"]
    pl = deps["pl"]
    TemporalFusionTransformer = deps["TemporalFusionTransformer"]
    TimeSeriesDataSet = deps["TimeSeriesDataSet"]
    if torch.cuda.is_available():
        torch.set_float32_matmul_precision("medium")
    pl.seed_everything(42, workers=True)

    processed = load_processed(args.data)
    training_df = train_tft.load_training_frame(args.data)
    training, _, _ = train_tft.build_datasets(training_df, deps, fast_dev_run=False, train_days=train_days)
    prediction_df, context = build_prediction_frame(processed)
    prediction_dataset = TimeSeriesDataSet.from_dataset(training, prediction_df, predict=True, stop_randomization=True)
    prediction_loader = prediction_dataset.to_dataloader(train=False, batch_size=args.batch_size, num_workers=args.num_workers)

    map_location = "cuda" if torch.cuda.is_available() else "cpu"
    if not torch.cuda.is_available():
        checkpoint = _make_cpu_safe_checkpoint(checkpoint, torch)
    model = TemporalFusionTransformer.load_from_checkpoint(str(checkpoint), map_location=map_location)
    prediction = model.predict(
        prediction_loader,
        mode="quantiles",
        return_index=True,
        trainer_kwargs={"accelerator": "auto", "devices": "auto", "logger": False},
    )

    nodes, forecasts, lives = build_payloads(prediction, context, corrections, args.source)
    issued_at = forecasts[nodes[0]["id"]]["issued_at"]
    nodes_payload = merge_synthetic_nodes(nodes, args.source, issued_at)

    write_json(args.out / "nodes.json", nodes_payload)
    for node_id, payload in forecasts.items():
        write_json(args.out / "forecast" / f"{node_id}.json", payload)
    for node_id, payload in lives.items():
        write_json(args.out / "live" / f"{node_id}.json", payload)

    print(f"Checkpoint: {checkpoint}")
    print(f"Calibration: {'disabled' if args.no_calibration else args.calibration}")
    print(f"Output: {args.out}")
    print("Wrote:")
    print(f"  nodes.json")
    for node_id in forecasts:
        print(f"  forecast/{node_id}.json")
        print(f"  live/{node_id}.json")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(130)
