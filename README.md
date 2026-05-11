# GridCast

**Probabilistic 10-day grid-stress forecasting for AI data-centre operators.**

[![GridCast Demo](https://img.youtube.com/vi/-OHXRK749SA/maxresdefault.jpg)](https://youtu.be/-OHXRK749SA)

🌐 Live demo: **[gridcast.dev](https://gridcast.dev)** &nbsp;·&nbsp; 🎥 Walkthrough: **[YouTube](https://youtu.be/-OHXRK749SA)**

---

## The problem

AI is becoming the largest new electricity consumer in a generation. Hyperscalers are signing power-purchase agreements measured in gigawatts, and a single AI training campus can now draw more electricity than a small city. Most of that load is being **co-located next to transmission hubs** — Ashburn (Dominion Hub), Santa Clara (CAISO-SP15), Houston (ERCOT) — because that's where fibre, water, and cheap interconnects are.

The grid those campuses plug into was not designed for this. Three things make the situation fragile:

### 1. Grids run with thin, time-varying headroom

The amount of "spare" capacity at any moment is much smaller than the nameplate suggests, and it swings hard with weather. There is no permanent surplus — it appears and disappears on the timescale of hours.

![Reserve headroom over time](notebooks/figures/01_reserve_headroom.png)

### 2. Demand is predictable from weather — until it isn't

Load is tightly coupled to temperature. Both extreme cold and extreme heat push demand up sharply, and the relationship is non-linear. This is what makes forecasting tractable in the first place — but it also means forecast errors cluster precisely during the moments that matter most (heatwaves, cold snaps, heat domes).

![Demand vs temperature](notebooks/figures/02_demand_vs_temperature.png)

### 3. Forecast errors cost real money — and they spike during stress

When the day-ahead demand forecast is wrong, the system buys make-up power in real time at much higher prices. The mismatch translates directly into dollars. The chart below shows how forecast error and the day-ahead/real-time price spread combine into imbalance cost — and how the largest losses are concentrated in a handful of stressed hours.

![Forecast error vs imbalance cost](notebooks/figures/tx_recent_04_forecast_error_vs_cost.png)

### The blast radius

When grid headroom collapses during an extreme weather event — Texas Winter Storm 2021, PJM Summer Heatwave 2023 — operators have no smooth lever to pull. The default response is **forced load-shedding**: rolling blackouts, often with hours of notice or less. AI data centres in the affected zone get curtailed without warning, training runs die, inference SLAs fail, and the grid still ends up strained.

**The missing piece is multi-day lead time.** An operator who knows ten days in advance that a heat dome will collide with peak load can pre-position workloads, shift inference to other regions, and coordinate demand-response credits with the ISO. None of that is possible at four hours' notice.

---

## The solution

GridCast forecasts **grid-stress probability** at four major US transmission nodes over a 10-day horizon, and translates that forecast into a single, operator-facing number: a **recommended power allocation %** for co-located AI tenants.

The thesis: AI workloads are uniquely well-suited to act as a flexible grid buffer. Training is interruptible, batch inference can be deferred, and latency-tolerant traffic can be shifted geographically. If the data centre knows the stress forecast, it can convert that flexibility into both grid stability and commercial demand-response credit.

**What the dashboard surfaces, per node:**

- Current stress status (Stable / Elevated / Stressed)
- Demand forecast with p10–p90 confidence bands over 10 days
- Hourly stress-probability ribbon
- 16-member GFS weather ensemble
- Recommended allocation (p50 + defensive p10 floor) per co-located data centre
- Replay mode for known historical events (Texas 2021, PJM 2023) to verify the model against ground truth

---

## How it works

### The forecasting model

GridCast uses a **Temporal Fusion Transformer (TFT)** trained per node on historical demand, weather, and weather-forecast data. The TFT was chosen specifically for:

- **Probabilistic output** — it predicts quantiles (p10 / p50 / p90), not point estimates. That uncertainty is what makes the "defensive allocation floor" meaningful.
- **Multi-horizon forecasting** — one model produces the full 10-day curve, not a chain of recursive predictions that compound error.
- **Native multi-feature input** — handles past demand, future weather forecasts, and static node metadata in one architecture.

The model was trained on a single consumer GPU. After training, the checkpoint is rewritten for CPU inference so it can run on commodity Code Engine containers.

### Hourly profiles tell the model what "normal" looks like

The TFT learns the diurnal and seasonal structure embedded in every node. The chart below shows the strong, repeatable hourly shape that gives the model its skill — but also the seasonal variation it has to absorb.

![Hourly profiles by season](notebooks/figures/04_hourly_profiles_by_season.png)

### The IBM stack

Two IBM services run the production path:

| Service | Role |
|---|---|
| **IBM Cloud Object Storage (COS)** | Stores everything the frontend reads — forecast JSON per node, live state, replay events, runtime artifacts (model checkpoint, calibration, processed features). Public-read bucket; Next.js fetches it directly over HTTPS. |
| **IBM Code Engine** | Runs the inference pipeline as a one-shot containerized job: downloads runtime artifacts from COS → runs TFT inference → applies quantile calibration → writes frontend JSON back to COS. Triggered on demand or on a schedule. |

**Future: IBM watsonx.ai** — for the next iteration, we plan to layer watsonx.ai (Granite) on top of the TFT outputs to generate per-node analyst briefs as downloadable PDFs. The TFT produces the numbers; watsonx interprets them into operator-facing language and recommended actions. Not in the current demo build — see [Demo scope](#demo-scope-vs-production) below.

### The frontend

Next.js (App Router) + TypeScript on Vercel, Mapbox for the geography, Visx for charts. All data flows through `lib/dataSource.ts`, which has a single env-var switch: `GRIDCAST_DATA_SOURCE=fixtures` for local dev, `=cos` for production. Zod validates every payload at the boundary.

---

## Results

GridCast's TFT was benchmarked against a **24-hour persistence forecast** — a strong baseline for electricity demand, because load has heavy daily seasonality.

| Metric | Persistence baseline | GridCast TFT | Improvement |
|---|---:|---:|---:|
| MAPE | 5.23% | **4.50%** | −0.73 pp (≈ 14% relative) |
| MAE | 740 MW | **648 MW** | −92 MW (≈ 12% relative) |

### Uncertainty calibration

The probabilistic forecast is only useful if the quantile bands actually contain the truth at the advertised rate. We applied quantile calibration on top of the raw TFT outputs:

| | Raw TFT | Calibrated |
|---|---:|---:|
| p10–p90 coverage | 58.1% | **80.0%** |

So the headline result:

> **Our GPU-trained TFT beat the persistence baseline by ~14% on MAPE, and calibration brought the p10–p90 forecast-interval coverage from 58% to 80%.**

This is a strong prototype, not yet a production-grade forecast. It is enough to demonstrate that the architecture works, the numbers move in the right direction, and the operator-facing dashboard is grounded in real signal — but a deployment would need per-node retraining, more years of training data, and continuous monitoring.

---

## Demo scope vs production

**This repo is a demo.** It tells the full story end-to-end on four nodes (Dominion Hub, CAISO-SP15, CAISO-NP15, ERCOT-Houston) with synthetic data filling in another dozen for the map UI. The goal is to make the product legible to operators and judges, not to ship a service.

**In production, the shape changes:**

- **Per-grid focus.** A real deployment serves one ISO at a time — PJM, ERCOT, CAISO — not a national map. Each ISO has its own data feeds, market structures, and operator workflows, and a single dashboard glossing over those differences is the wrong product.
- **Native UI per grid.** Operators inside ERCOT work very differently from operators inside CAISO. The production version would ship a tailored interface per ISO instead of a generic map view.
- **Continuous retraining + monitoring.** The demo trains once and serves the resulting checkpoint. Production needs nightly retraining, drift detection, and per-quantile recalibration as conditions change.
- **watsonx.ai analyst briefs.** Currently the dashboard surfaces TFT outputs directly. The production roadmap adds an LLM interpretation layer (watsonx.ai + Granite) that generates per-node briefs as downloadable PDFs — the same artifact a human analyst would write, generated in seconds.

---

## Repo layout

```
app/                   Next.js routes and pages
components/            UI components (map, panel, charts, replay shell)
lib/
  dataSource.ts        Fixtures/COS switch + Zod validation
  formulas.ts          Stress level + recommended allocation math
  types.ts             Shared types for the API contract
fixtures/              Local JSON fixtures (dev mode)
backend/
  models/              TFT training, inference, calibration, Code Engine job
  data/                Data pulls (EIA, ERCOT, weather), feature building
notebooks/             Problem-framing analyses + figures
  figures/             Charts used in this README
SPEC.md                Frozen API contract + component tree
gridcast_design.tex    Original design doc
```

## Quick start

```bash
pnpm install
cp .env.example .env.local         # set NEXT_PUBLIC_MAPBOX_TOKEN
pnpm dev                            # serves with local fixtures
```

For the inference pipeline (Python venv required):

```powershell
.\.venv\Scripts\python.exe backend\models\run_inference_pipeline.py
```

See `backend/models/CODE_ENGINE.md` for the IBM Code Engine deployment flow.

---

## Acknowledgements

Demand data from EIA, ERCOT, and CAISO public APIs. Weather data from Open-Meteo. Map basemap by Mapbox. TFT implementation built on PyTorch Forecasting.
