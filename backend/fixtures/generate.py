"""GridCast synthetic fixture generator.

NOTE: Partially superseded by PLAN.md. This generator currently emits the
older 5-endpoint shape with `stress` as the primary forecast field. The
target API contract (PLAN.md) is 4 endpoints with `demand_mw` quantiles
as the primary forecast field, kebab-case node IDs, plus `ensemble_spread`
and `data_centers` fields. Reconciliation table in PLAN.md tracks the
full diff. This file will be rewritten once the real TFT outputs land.

Outputs (under ./out/):
    nodes.json
    forecast_<node_id>.json     x4
    live_<node_id>.json         x4
    replay_<event_id>.json      x3
"""

import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

NOW = datetime(2026, 5, 9, 14, 0, 0, tzinfo=timezone.utc)
SEED = 42


# ---------------------------------------------------------------------------
# Node catalog
# ---------------------------------------------------------------------------

NODES = [
    {
        "id": "dominion_hub",
        "name": "Dominion Hub",
        "balancing_authority": "PJM",
        "region": "Northern Virginia",
        "description": "Largest data center corridor in the world",
        "lat": 38.95,
        "lon": -77.45,
        "baseline_demand_mw": 19000,
        "summer_peak_demand_mw": 24000,
        "winter_peak_demand_mw": 21000,
        "fuel_mix": {
            "natural_gas": 0.42, "nuclear": 0.28, "coal": 0.10,
            "wind": 0.08, "solar": 0.07, "hydro": 0.03, "other": 0.02,
        },
        "stress_base_may": 0.48,
        "diurnal": "double_peak",
        "utc_offset_h": -4,  # EDT
    },
    {
        "id": "caiso_sp15",
        "name": "CAISO SP15",
        "balancing_authority": "CAISO",
        "region": "Southern California (LA basin)",
        "description": "Duck curve poster child; solar surplus midday, steep evening ramp",
        "lat": 34.05,
        "lon": -118.24,
        "baseline_demand_mw": 14000,
        "summer_peak_demand_mw": 22000,
        "winter_peak_demand_mw": 15000,
        "fuel_mix": {
            "solar": 0.32, "natural_gas": 0.30, "wind": 0.12,
            "nuclear": 0.08, "hydro": 0.10, "imports": 0.06, "other": 0.02,
        },
        "stress_base_may": 0.50,
        "diurnal": "duck_curve",
        "utc_offset_h": -7,  # PDT
    },
    {
        "id": "caiso_np15",
        "name": "CAISO NP15",
        "balancing_authority": "CAISO",
        "region": "Northern California (Bay Area)",
        "description": "Bay Area tech hub load; mild climate, lower baseline stress",
        "lat": 37.77,
        "lon": -122.42,
        "baseline_demand_mw": 11000,
        "summer_peak_demand_mw": 16000,
        "winter_peak_demand_mw": 12000,
        "fuel_mix": {
            "solar": 0.24, "natural_gas": 0.22, "hydro": 0.20,
            "wind": 0.14, "nuclear": 0.10, "imports": 0.08, "other": 0.02,
        },
        "stress_base_may": 0.30,
        "diurnal": "duck_curve",
        "utc_offset_h": -7,  # PDT
    },
    {
        "id": "ercot_houston",
        "name": "ERCOT Houston Hub",
        "balancing_authority": "ERCOT",
        "region": "Houston, Texas",
        "description": "Gulf Coast load center; AC-driven summer peak, exposed to winter cold snaps",
        "lat": 29.76,
        "lon": -95.37,
        "baseline_demand_mw": 16000,
        "summer_peak_demand_mw": 25000,
        "winter_peak_demand_mw": 20000,
        "fuel_mix": {
            "natural_gas": 0.46, "wind": 0.22, "coal": 0.14,
            "nuclear": 0.08, "solar": 0.08, "other": 0.02,
        },
        "stress_base_may": 0.55,
        "diurnal": "ac_ramp",
        "utc_offset_h": -5,  # CDT
    },
]

NODES_BY_ID = {n["id"]: n for n in NODES}


# ---------------------------------------------------------------------------
# Shape helpers
# ---------------------------------------------------------------------------

def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def stress_level(s: float) -> str:
    if s < 0.40:
        return "green"
    if s < 0.70:
        return "yellow"
    return "red"


def diurnal_component(hour: int, kind: str) -> float:
    """Return a [-1, 1]-ish diurnal stress modifier for a given local hour.

    Uses peak_at(h, p) = cos((h-p)/24 * 2pi), which is +1 at h=p and -1 twelve
    hours away. Composing peaks/dips this way keeps the phase obvious.
    """
    def peak_at(h: int, peak_h: int) -> float:
        return math.cos((h - peak_h) / 24 * 2 * math.pi)

    if kind == "duck_curve":
        # Evening ramp peak (~19h local) and midday solar dip (~13h local).
        return 0.7 * peak_at(hour, 19) - 0.5 * peak_at(hour, 13)
    if kind == "ac_ramp":
        # Late-afternoon AC peak (~16h local).
        return peak_at(hour, 16)
    # default double peak: morning rush + evening
    return 0.55 * peak_at(hour, 7) + 0.55 * peak_at(hour, 19)


def weekly_component(weekday: int) -> float:
    return 0.0 if weekday < 5 else -0.12


def seasonal_component(day_of_year: int) -> float:
    """Slight seasonal lean: spring/fall mild, summer/winter higher."""
    return -0.10 * math.cos((day_of_year - 15) / 365 * 2 * math.pi)


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def quantile_band(p50: float, horizon_h: int, base_spread: float = 0.04) -> dict:
    """Build a 5-quantile band that widens with horizon. Spread grows ~ sqrt(t)."""
    spread = base_spread + 0.018 * math.sqrt(max(horizon_h, 1))
    return {
        "p10": round(clamp(p50 - 1.28 * spread), 4),
        "p25": round(clamp(p50 - 0.67 * spread), 4),
        "p50": round(clamp(p50), 4),
        "p75": round(clamp(p50 + 0.67 * spread), 4),
        "p90": round(clamp(p50 + 1.28 * spread), 4),
    }


def demand_band(mw: float, horizon_h: int, base_pct: float = 0.03) -> dict:
    spread_pct = base_pct + 0.012 * math.sqrt(max(horizon_h, 1))
    return {
        "p10": round(mw * (1 - 1.28 * spread_pct), 1),
        "p50": round(mw, 1),
        "p90": round(mw * (1 + 1.28 * spread_pct), 1),
    }


# ---------------------------------------------------------------------------
# Time series generators
# ---------------------------------------------------------------------------

def stress_at(node: dict, dt: datetime, rng: random.Random,
              event_modifier: float = 0.0) -> float:
    """Compose a stress value in [0, 1] for a given node at a given UTC time."""
    base = node["stress_base_may"]
    local_hour = (dt.hour + node["utc_offset_h"]) % 24
    diurnal = 0.18 * diurnal_component(local_hour, node["diurnal"])
    weekly = weekly_component(dt.weekday())
    seasonal = seasonal_component(dt.timetuple().tm_yday)
    noise = rng.gauss(0, 0.02)
    return clamp(base + diurnal + weekly + seasonal + event_modifier + noise)


def demand_at(node: dict, stress: float, rng: random.Random) -> float:
    base = node["baseline_demand_mw"]
    peak = node["summer_peak_demand_mw"]
    headroom = peak - base
    mw = base + headroom * (stress - 0.3) + rng.gauss(0, base * 0.01)
    return max(mw, base * 0.6)


def lmp_at(stress: float, rng: random.Random) -> float:
    """Crude LMP curve: ~$25 baseline, scarcity shoots it up exponentially."""
    return round(25 + 80 * stress + 400 * max(0, stress - 0.75) ** 2 + rng.gauss(0, 3), 2)


# ---------------------------------------------------------------------------
# Endpoint payload builders
# ---------------------------------------------------------------------------

def build_nodes_payload() -> dict:
    rng = random.Random(SEED)
    nodes_out = []
    for n in NODES:
        s = stress_at(n, NOW, rng)
        nodes_out.append({
            "id": n["id"],
            "name": n["name"],
            "balancing_authority": n["balancing_authority"],
            "region": n["region"],
            "description": n["description"],
            "lat": n["lat"],
            "lon": n["lon"],
            "current_stress": round(s, 4),
            "stress_level": stress_level(s),
            "allocation": {
                # higher stress -> recommend allocating less excess capacity
                "percent": int(round(80 - 70 * s)),
                "confidence": round(0.92 - 0.20 * s, 2),
                "horizon_days": 10,
            },
            "updated_at": iso(NOW),
        })
    return {"generated_at": iso(NOW), "nodes": nodes_out}


def build_forecast_payload(node: dict) -> dict:
    rng = random.Random(SEED + hash(node["id"]) % 10_000)
    points = []
    for h in range(1, 241):  # 1..240 hours ahead
        ts = NOW + timedelta(hours=h)
        s = stress_at(node, ts, rng)
        mw = demand_at(node, s, rng)
        points.append({
            "timestamp": iso(ts),
            "horizon_hours": h,
            "stress": quantile_band(s, h),
            "demand_mw": demand_band(mw, h),
        })
    headline_s = points[0]["stress"]["p50"]
    return {
        "node_id": node["id"],
        "generated_at": iso(NOW),
        "horizon_hours": 240,
        "timestep_hours": 1,
        "model": "TFT-v0-synthetic",
        "units": {"stress": "normalized 0-1", "demand_mw": "MW"},
        "allocation_recommendation": {
            "percent": int(round(80 - 70 * headline_s)),
            "confidence": round(0.92 - 0.20 * headline_s, 2),
            "horizon_days": 10,
            "rationale": (
                "Excess capacity recommendation derived from P90 of stress "
                "forecast across the 10-day horizon."
            ),
        },
        "points": points,
    }


def build_live_payload(node: dict) -> dict:
    rng = random.Random(SEED + 1 + hash(node["id"]) % 10_000)
    s_now = stress_at(node, NOW, rng)
    mw_now = demand_at(node, s_now, rng)

    last_7 = []
    for h in range(168, 0, -1):  # 7 days ago -> 1 hour ago
        ts = NOW - timedelta(hours=h)
        s = stress_at(node, ts, rng)
        actual = demand_at(node, s, rng)
        # forecast was a slightly biased version of actual
        forecast = actual * (1 + rng.gauss(0, 0.025))
        last_7.append({
            "timestamp": iso(ts),
            "actual_demand_mw": round(actual, 1),
            "forecast_demand_mw": round(forecast, 1),
        })

    return {
        "node_id": node["id"],
        "timestamp": iso(NOW),
        "demand_mw": round(mw_now, 1),
        "lmp_usd_per_mwh": lmp_at(s_now, rng),
        "fuel_mix": node["fuel_mix"],
        "current_stress": round(s_now, 4),
        "stress_level": stress_level(s_now),
        "last_7_days": last_7,
    }


# ---------------------------------------------------------------------------
# Replay events
# ---------------------------------------------------------------------------

REPLAY_EVENTS = [
    {
        "event_id": "texas_winter_2021",
        "title": "Winter Storm Uri (February 2021)",
        "description": (
            "Multi-day arctic blast knocked ~50% of ERCOT generation offline. "
            "Houston load center demand spiked while gas wells froze."
        ),
        "hero_node": "ercot_houston",
        "start": datetime(2021, 2, 13, 0, 0, 0, tzinfo=timezone.utc),
        "end":   datetime(2021, 2, 19, 0, 0, 0, tzinfo=timezone.utc),
        "peak":  datetime(2021, 2, 15, 8, 0, 0, tzinfo=timezone.utc),
        "peak_modifier": 0.45,
    },
    {
        "event_id": "pnw_heat_dome_2022",
        "title": "Pacific Northwest Heat Dome (Summer 2022)",
        "description": (
            "Persistent high-pressure ridge drove unprecedented heat into the "
            "PNW; CAISO NP15 sustained yellow stress for the better part of a week."
        ),
        "hero_node": "caiso_np15",
        "start": datetime(2022, 7, 25, 0, 0, 0, tzinfo=timezone.utc),
        "end":   datetime(2022, 7, 31, 0, 0, 0, tzinfo=timezone.utc),
        "peak":  datetime(2022, 7, 28, 23, 0, 0, tzinfo=timezone.utc),
        "peak_modifier": 0.30,
    },
    {
        "event_id": "pjm_summer_2023",
        "title": "PJM Mid-Atlantic Summer Stress (August 2023)",
        "description": (
            "Heat wave + heavy data center load pushed Dominion Hub into red. "
            "PJM issued maximum generation alerts for two consecutive afternoons."
        ),
        "hero_node": "dominion_hub",
        "start": datetime(2023, 8, 14, 0, 0, 0, tzinfo=timezone.utc),
        "end":   datetime(2023, 8, 20, 0, 0, 0, tzinfo=timezone.utc),
        "peak":  datetime(2023, 8, 17, 22, 0, 0, tzinfo=timezone.utc),
        "peak_modifier": 0.40,
    },
]


def event_modifier(event: dict, dt: datetime, node: dict) -> float:
    """Bell-shaped bump centered on event peak; only the hero node feels it strongly."""
    delta_h = abs((dt - event["peak"]).total_seconds()) / 3600.0
    sigma = 36.0  # 1.5-day stdev
    bell = math.exp(-(delta_h ** 2) / (2 * sigma ** 2))
    factor = 1.0 if node["id"] == event["hero_node"] else 0.15
    return event["peak_modifier"] * bell * factor


def build_replay_payload(event: dict) -> dict:
    rng = random.Random(SEED + 2 + hash(event["event_id"]) % 10_000)

    # Actual timeline at 1-hour resolution.
    timeline = []
    t = event["start"]
    while t <= event["end"]:
        node_states = []
        for n in NODES:
            mod = event_modifier(event, t, n)
            s = stress_at(n, t, rng, event_modifier=mod)
            node_states.append({
                "node_id": n["id"],
                "stress": round(s, 4),
                "stress_level": stress_level(s),
            })
        timeline.append({"timestamp": iso(t), "node_states": node_states})
        t += timedelta(hours=1)

    # The "we'd have predicted this 72h early" punchline:
    # forecast issued 72h before peak, hero node, 240h horizon.
    issued_at = event["peak"] - timedelta(hours=72)
    hero = NODES_BY_ID[event["hero_node"]]
    pre_event_forecast = []
    for h in range(1, 121):  # next 5 days from issuance covers the peak
        ts = issued_at + timedelta(hours=h)
        mod = event_modifier(event, ts, hero)
        s = stress_at(hero, ts, rng, event_modifier=mod)
        pre_event_forecast.append({
            "timestamp": iso(ts),
            "horizon_hours": h,
            "stress": quantile_band(s, h),
        })

    return {
        "event_id": event["event_id"],
        "title": event["title"],
        "description": event["description"],
        "hero_node": event["hero_node"],
        "start": iso(event["start"]),
        "end": iso(event["end"]),
        "peak": iso(event["peak"]),
        "predicted_at": iso(issued_at),
        "pre_event_forecast": {
            "node_id": hero["id"],
            "generated_at": iso(issued_at),
            "horizon_hours": 120,
            "timestep_hours": 1,
            "points": pre_event_forecast,
        },
        "actual_timeline": timeline,
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def write(name: str, payload) -> None:
    path = OUT / name
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(OUT.parent)} ({path.stat().st_size:,} bytes)")


def main() -> None:
    print(f"GridCast fixtures -> {OUT}")
    write("nodes.json", build_nodes_payload())
    for n in NODES:
        write(f"forecast_{n['id']}.json", build_forecast_payload(n))
        write(f"live_{n['id']}.json", build_live_payload(n))
    for e in REPLAY_EVENTS:
        write(f"replay_{e['event_id']}.json", build_replay_payload(e))
    print("done.")


if __name__ == "__main__":
    main()
