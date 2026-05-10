#!/usr/bin/env python3
"""Generate deterministic GridCast demo fixtures from the SPEC.md contract."""

from __future__ import annotations

import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED = 20260509
ISSUED_AT = "2026-05-09T14:00:00Z"
PUBLISHED_AT = "2026-05-09T13:55:00Z"
SOURCE = "fixtures"
HORIZON = 240
HISTORY = 168
MEMBERS = 16


NODES = {
    "dominion-hub": {
        "name": "Dominion Hub",
        "iso": "PJM",
        "state": "VA",
        "ba_code": "PJM",
        "lat": 38.9,
        "lon": -77.0,
        "threshold": 52.0,
        "base": 30.0,
        "amp": 7.5,
        "temp": 24.0,
    },
    "caiso-sp15": {
        "name": "CAISO SP15",
        "iso": "CAISO",
        "state": "CA",
        "ba_code": "CAISO",
        "lat": 34.05,
        "lon": -118.25,
        "threshold": 50.0,
        "base": 28.0,
        "amp": 6.0,
        "temp": 21.0,
    },
    "caiso-np15": {
        "name": "CAISO NP15",
        "iso": "CAISO",
        "state": "CA",
        "ba_code": "CAISO",
        "lat": 37.77,
        "lon": -122.42,
        "threshold": 42.0,
        "base": 24.0,
        "amp": 4.8,
        "temp": 17.0,
    },
    "ercot-houston": {
        "name": "ERCOT Houston",
        "iso": "ERCOT",
        "state": "TX",
        "ba_code": "ERCOT",
        "lat": 29.76,
        "lon": -95.37,
        "threshold": 62.0,
        "base": 33.0,
        "amp": 9.5,
        "temp": 30.0,
    },
}


DATA_CENTERS = {
    "dominion-hub": [
        ("aws-ashburn", "AWS Ashburn Campus", "AWS", 1200),
        ("azure-east", "Microsoft Azure East", "Microsoft", 800),
        ("google-loudoun", "Google Loudoun", "Google", 650),
    ],
    "caiso-sp15": [
        ("azure-west", "Microsoft Azure West", "Microsoft", 500),
        ("google-west-la", "Google West-LA", "Google", 400),
        ("meta-sandstone", "Meta Sandstone", "Meta", 350),
    ],
    "caiso-np15": [
        ("google-bay-west", "Google Bay-West", "Google", 600),
        ("meta-mpk-campus", "Meta MPK Campus", "Meta", 500),
        ("nvidia-santa-clara", "NVIDIA Santa Clara", "NVIDIA", 300),
    ],
    "ercot-houston": [
        ("azure-tx", "Microsoft Azure TX", "Microsoft", 700),
        ("aws-tx-east", "AWS TX-East", "AWS", 550),
        ("google-south-tx", "Google South-TX", "Google", 450),
    ],
}


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def round1(value: float) -> float:
    return round(value, 1)


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def tier(capacity: int) -> str:
    if capacity >= 700:
        return "large"
    if capacity >= 400:
        return "medium"
    return "small"


def hourly_timestamps(start: datetime, count: int) -> list[str]:
    return [iso(start + timedelta(hours=i)) for i in range(count)]


def bump(h: int, center: float, width: float, height: float) -> float:
    return height * math.exp(-((h - center) / width) ** 2)


def node_adjustment(node_id: str, h: int, hour: int) -> float:
    if node_id == "ercot-houston":
        return bump(h, 128, 46, 18) + bump(h, 160, 24, 8)
    if node_id == "caiso-sp15":
        evening_ramp = bump(hour, 20, 3.2, 15)
        midday_duck = -bump(hour, 13, 4.0, 8)
        return evening_ramp + midday_duck + bump(h, 150, 34, 6)
    if node_id == "dominion-hub":
        return bump(h, 84, 30, 11) + bump(h, 112, 24, 7)
    return bump(h, 138, 40, 3)


def lmp_value(node_id: str, h: int, start: datetime, history: bool = False) -> float:
    cfg = NODES[node_id]
    ts = start + timedelta(hours=h)
    hour = ts.hour
    diurnal = cfg["amp"] * (0.55 + 0.45 * math.sin((hour - 15) / 24 * 2 * math.pi))
    weekly = 3.0 * math.sin((h + (35 if history else 0)) / 168 * 2 * math.pi - 0.6)
    shoulder = 1.7 * math.sin(h / 18 * 2 * math.pi)
    trend = (h / max(HORIZON - 1, 1)) * (2.5 if node_id in {"ercot-houston", "caiso-sp15"} else 1.2)
    value = cfg["base"] + diurnal + weekly + shoulder + trend + node_adjustment(node_id, h, hour)
    if history:
        value += 2.2 * math.sin(h / 9 * 2 * math.pi)
    return max(8.0, value)


def build_quantiles(node_id: str, start: datetime) -> dict[str, list[float] | list[str]]:
    timestamps = hourly_timestamps(start, HORIZON)
    p10: list[float] = []
    p25: list[float] = []
    p50: list[float] = []
    p75: list[float] = []
    p90: list[float] = []
    for h in range(HORIZON):
        median = lmp_value(node_id, h, start)
        spread = 4.5 + 0.038 * h
        if node_id == "ercot-houston":
            spread += 1.8 + bump(h, 135, 50, 5)
        elif node_id == "caiso-sp15":
            spread += bump((start + timedelta(hours=h)).hour, 20, 3.5, 3.5)
        elif node_id == "dominion-hub":
            spread += bump(h, 95, 36, 2.8)
        low = max(4.0, median - spread * 1.15)
        p10.append(round1(low))
        p25.append(round1(max(low, median - spread * 0.55)))
        p50.append(round1(median))
        p75.append(round1(median + spread * 0.55))
        p90.append(round1(median + spread * 1.15))
    return {"timestamps": timestamps, "p10": p10, "p25": p25, "p50": p50, "p75": p75, "p90": p90}


def build_history(node_id: str, end: datetime) -> dict[str, list[float] | list[str]]:
    start = end - timedelta(hours=HISTORY - 1)
    timestamps = hourly_timestamps(start, HISTORY)
    values = [round1(lmp_value(node_id, h, start, history=True)) for h in range(HISTORY)]
    return {"timestamps": timestamps, "lmp_congestion_usd": values}


def stress_probability(p90: float, threshold: float, h: int) -> float:
    clustered = 0.05 * math.sin(h / 18 * 2 * math.pi) + 0.03 * math.sin(h / 71 * 2 * math.pi)
    return max(0.0, min(1.0, round(sigmoid((p90 - threshold - 5.4) / 4.5) + clustered, 3)))


def allocation_from_forecast(forecast: dict[str, list[float] | list[str]], threshold: float) -> dict[str, float | int]:
    p90 = forecast["p90"]
    p50 = forecast["p50"]
    p10 = forecast["p10"]
    assert isinstance(p90, list) and isinstance(p50, list) and isinstance(p10, list)
    p90_fraction = sum(1 for value in p90 if value >= threshold) / HORIZON
    p50_fraction = sum(1 for value in p50 if value >= threshold) / HORIZON
    p10_fraction = sum(1 for value in p10 if value >= threshold) / HORIZON
    return {
        "pct": round((1 - p90_fraction) * 100),
        "pct_p50": round((1 - p50_fraction) * 100),
        "pct_p10": round((1 - p10_fraction) * 100),
        "p90_stress_fraction": round(p90_fraction, 4),
    }


def build_stress_timeline(forecast: dict[str, list[float] | list[str]], threshold: float) -> list[dict[str, float | int]]:
    p90 = forecast["p90"]
    assert isinstance(p90, list)
    return [
        {"hour_offset": h, "stress_probability": stress_probability(float(value), threshold, h)}
        for h, value in enumerate(p90)
    ]


def build_ensemble(node_id: str, timestamps: list[str]) -> dict[str, str | list[str] | list[list[float]]]:
    rng = random.Random(f"{SEED}:{node_id}:ensemble")
    cfg = NODES[node_id]
    members: list[list[float]] = []
    offsets = [i - (MEMBERS - 1) / 2 for i in range(MEMBERS)]
    for member_idx, offset in enumerate(offsets):
        phase = rng.uniform(-0.8, 0.8)
        member: list[float] = []
        for h in range(HORIZON):
            ts = dt(timestamps[h])
            daily = 4.2 * math.sin((ts.hour - 14) / 24 * 2 * math.pi)
            horizon_spread = 0.12 + (h / (HORIZON - 1)) * 0.55
            synoptic = 1.6 * math.sin((h / 48 * 2 * math.pi) + phase)
            if node_id == "ercot-houston":
                synoptic += bump(h, 128, 45, 5.5)
            elif node_id == "dominion-hub":
                synoptic += bump(h, 92, 36, 3.2)
            value = cfg["temp"] + daily + synoptic + offset * horizon_spread + rng.uniform(-0.15, 0.15)
            member.append(round1(value))
        members.append(member)
    return {"variable": "temperature_2m", "unit": "celsius", "timestamps": timestamps, "members": members}


def build_data_centers(node_id: str, allocation: dict[str, float | int]) -> list[dict[str, object]]:
    pct = int(allocation["pct"])
    pct_p50 = int(allocation["pct_p50"])
    pct_p10 = int(allocation["pct_p10"])
    centers = []
    for dc_id, name, operator, capacity in DATA_CENTERS[node_id]:
        centers.append(
            {
                "id": dc_id,
                "name": name,
                "operator": operator,
                "tier": tier(capacity),
                "capacity_mw": capacity,
                "committed_draw_mw": {
                    "p10": round(capacity * pct_p10 / 100),
                    "p50": round(capacity * pct_p50 / 100),
                    "p90": round(capacity * pct / 100),
                },
            }
        )
    return centers


def build_forecast(node_id: str, issued_at: str, published_at: str, forecast_start: datetime | None = None) -> dict[str, object]:
    issue_dt = dt(issued_at)
    start = forecast_start or issue_dt + timedelta(hours=1)
    cfg = NODES[node_id]
    forecast = build_quantiles(node_id, start)
    allocation = allocation_from_forecast(forecast, cfg["threshold"])
    timestamps = forecast["timestamps"]
    assert isinstance(timestamps, list)
    return {
        "node_id": node_id,
        "schema_version": 1,
        "issued_at": issued_at,
        "published_at": published_at,
        "source": SOURCE,
        "horizon_hours": HORIZON,
        "encoder_hours": HISTORY,
        "quantile_levels": [0.1, 0.25, 0.5, 0.75, 0.9],
        "stress_threshold_lmp_usd": cfg["threshold"],
        "history": build_history(node_id, start - timedelta(hours=1)),
        "forecast": forecast,
        "allocation": allocation,
        "stress_timeline": build_stress_timeline(forecast, cfg["threshold"]),
        "ensemble_spread": build_ensemble(node_id, timestamps),
        "data_centers": build_data_centers(node_id, allocation),
    }


def build_live(node_id: str) -> dict[str, object]:
    live_values = {
        "dominion-hub": (95000, 92000, 22.5, 4.2),
        "caiso-sp15": (30800, 29500, 24.8, 3.6),
        "caiso-np15": (24800, 25200, 18.4, 5.1),
        "ercot-houston": (78200, 72400, 34.6, 3.1),
    }
    demand, demand_forecast, temp, wind = live_values[node_id]
    deviation = round((demand - demand_forecast) / demand_forecast * 100, 1)
    return {
        "node_id": node_id,
        "schema_version": 1,
        "fetched_at": ISSUED_AT,
        "source": SOURCE,
        "eia": {
            "demand_mw": demand,
            "demand_forecast_mw": demand_forecast,
            "demand_deviation_pct": deviation,
        },
        "weather": {
            "temperature_2m_c": temp,
            "wind_speed_10m_ms": wind,
            "ensemble_member_count": MEMBERS,
        },
    }


def build_nodes(forecasts: dict[str, dict[str, object]]) -> dict[str, object]:
    nodes = []
    for node_id, cfg in NODES.items():
        forecast = forecasts[node_id]
        allocation = forecast["allocation"]
        assert isinstance(allocation, dict)
        stress_timeline = forecast["stress_timeline"]
        assert isinstance(stress_timeline, list)
        avg_stress = round(sum(float(point["stress_probability"]) for point in stress_timeline) / HORIZON, 3)
        nodes.append(
            {
                "id": node_id,
                "name": cfg["name"],
                "iso": cfg["iso"],
                "state": cfg["state"],
                "ba_code": cfg["ba_code"],
                "lat": cfg["lat"],
                "lon": cfg["lon"],
                "stress_probability": avg_stress,
                "allocation_pct": allocation["pct"],
            }
        )
    return {
        "schema_version": 1,
        "issued_at": ISSUED_AT,
        "published_at": PUBLISHED_AT,
        "source": SOURCE,
        "nodes": nodes,
    }


def build_replay(event_id: str) -> dict[str, object]:
    if event_id == "texas-2021":
        node_id = "ercot-houston"
        issued = "2021-02-04T00:00:00Z"
        actual_event_date = "2021-02-15T00:00:00Z"
        start = dt("2021-02-09T00:00:00Z")
        event_name = "Texas Winter Storm Uri"
        narrative = "Forecast as it would have appeared on Feb 4, 2021 - 10 days before the storm peak."
    else:
        node_id = "dominion-hub"
        issued = "2023-07-18T00:00:00Z"
        actual_event_date = "2023-07-27T00:00:00Z"
        start = dt("2023-07-22T00:00:00Z")
        event_name = "PJM Summer Heatwave"
        narrative = "Forecast as it would have appeared before the late-July PJM heatwave."

    payload = build_forecast(node_id, issued, PUBLISHED_AT, start)
    forecast = payload["forecast"]
    assert isinstance(forecast, dict)
    timestamps = forecast["timestamps"]
    p90 = forecast["p90"]
    assert isinstance(timestamps, list) and isinstance(p90, list)
    actuals: list[float] = []
    for h, upper in enumerate(p90):
        base = float(upper)
        if event_id == "texas-2021":
            spike = bump(h, 142, 16, 270) + bump(h, 156, 8, 190)
            realized = base * 0.82 + 8 * math.sin(h / 8) + spike
        else:
            spike = bump(h, 130, 28, 42) + bump(h, 166, 22, 28)
            realized = base * 0.9 + 4 * math.sin(h / 10) + spike
        actuals.append(round1(max(0.0, realized)))

    payload.update(
        {
            "event_id": event_id,
            "event_name": event_name,
            "actual_event_date": actual_event_date,
            "narrative": narrative,
            "actuals_overlay": {
                "timestamps": timestamps,
                "lmp_congestion_usd": actuals,
            },
        }
    )
    return payload


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    forecasts = {node_id: build_forecast(node_id, ISSUED_AT, PUBLISHED_AT) for node_id in NODES}
    write_json(ROOT / "nodes.json", build_nodes(forecasts))
    for node_id, payload in forecasts.items():
        write_json(ROOT / "forecast" / f"{node_id}.json", payload)
        write_json(ROOT / "live" / f"{node_id}.json", build_live(node_id))
    for event_id in ("texas-2021", "pjm-2023"):
        write_json(ROOT / "replay" / f"{event_id}.json", build_replay(event_id))


if __name__ == "__main__":
    main()
