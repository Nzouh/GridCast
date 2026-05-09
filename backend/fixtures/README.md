# GridCast fixtures

Synthetic JSON fixtures matching the 5-endpoint API contract from
[`DESIGN_WALKTHROUGH.md`](../../DESIGN_WALKTHROUGH.md). Used to unblock
frontend work before the real ingestion + TFT inference pipeline lands.

## Regenerating

```
python backend/fixtures/generate.py
```

Pure stdlib, deterministic (seed = 42). Outputs land in `backend/fixtures/out/`.
Move/symlink them into the frontend wherever Person B prefers.

## Files and shapes

All endpoints return JSON. `<id>` is one of `dominion_hub`, `caiso_sp15`,
`caiso_np15`, `ercot_houston`. `<event_id>` is one of `texas_winter_2021`,
`pnw_heat_dome_2022`, `pjm_summer_2023`.

| File | Endpoint | Notes |
|---|---|---|
| `nodes.json` | `GET /api/nodes` | Top-level list of 4 nodes with current stress + allocation. Map markers read from here. |
| `forecast_<id>.json` | `GET /api/nodes/{id}/forecast` | 240 hourly points, 5-quantile band per point (`p10/p25/p50/p75/p90`), bands widen with horizon. |
| `live_<id>.json` | `GET /api/nodes/{id}/live` | Current demand, LMP, fuel mix, plus 168h of `actual_demand_mw` vs `forecast_demand_mw`. |
| `replay_<event_id>.json` | `GET /api/replay/{event_id}` | Hourly `actual_timeline` covering the event window + a `pre_event_forecast` issued 72h before peak (the "we'd have predicted this" panel). |
| `refresh_response.json` | `POST /api/nodes/{id}/refresh` | Example success response. The actual route just re-reads from COS and returns this shape. |

## Conventions

- All timestamps are ISO-8601 UTC with `Z` suffix.
- `stress` is normalized to `[0, 1]`. Color thresholds: `< 0.40` green,
  `0.40 - 0.70` yellow, `> 0.70` red. The `stress_level` string is included
  for convenience.
- `allocation.percent` is the recommended share of excess capacity (0-100).
  Higher node stress -> lower recommended allocation.
- `allocation.confidence` is in `[0, 1]`. The headline UI string is built as
  `"{percent}% of excess capacity, {confidence*100:.0f}% confidence"`.
- Forecast points include `horizon_hours` so charts can index by lead time
  without parsing timestamps.

## What's "synthetic" vs. "real" here

Numbers are generated to be plausible, not real:

- Per-node baselines from public PJM/CAISO/ERCOT load order-of-magnitude.
- Diurnal shape per node story: SP15 duck curve (midday solar dip, evening
  ramp peak), Houston AC ramp (afternoon peak), Dominion double peak
  (morning + evening), NP15 milder version of the duck curve.
- Forecast bands widen as `~ sqrt(horizon)` (matches how a quantile model's
  uncertainty grows with lead time).
- Replay events apply a bell-shaped stress bump centered on the historical
  peak time, mostly affecting the hero node. The pre-event forecast issued
  72h before the peak intentionally shows P90 reaching the red zone — that's
  the demo punchline.

When real data lands (Phase 1-4 of the design doc), the same JSON shapes
should be emitted by the inference script and dropped into IBM COS at the
same filenames. Frontend integration becomes a base-URL swap.

## Sanity-checking after a regen

Quick visual:

```
python -c "
import json
n = json.load(open('backend/fixtures/out/nodes.json'))['nodes']
for x in n:
    print(f'{x[\"id\"]:<16} stress={x[\"current_stress\"]:.2f} ({x[\"stress_level\"]})  alloc={x[\"allocation\"][\"percent\"]}%')
"
```

Expected (May, no events): NP15 green, the others yellow, Houston the
hottest.
