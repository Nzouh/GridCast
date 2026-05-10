# GridCast — Design Walkthrough

> **⚠️ SUPERSEDED in part by [PLAN.md](PLAN.md).** This walkthrough is preserved
> for product narrative and high-level architecture context. Where it conflicts
> with PLAN.md, **PLAN.md wins**. Specifically:
> - TFT target = **demand (MW)**, not stress or LMP congestion
> - **4 API endpoints** (no `POST /refresh`)
> - **2 replay events** in UI (Texas 2021, PJM 2023). PNW 2022 dropped from UI but kept as an EDA case-study chart
> - Stress thresholds: `green<0.20, amber 0.20–0.50, red≥0.50` (derived from demand quantiles)
> - Light fintech theme (sf.atmo.ai), not dark-mode
> - Frontend: Next.js App Router + RSC; backend: Next.js API routes reading IBM COS objects directly (FastAPI on Code Engine is the production upgrade path, not the demo path)

This document walks through the GridCast product from two perspectives:
1. **The user's perspective** — what a person sees, clicks, and learns
2. **The developer's perspective** — what gets built, in what order, by whom

It reflects all decisions locked in so far: Option B architecture (pre-computed forecasts on COS), Next.js frontend on Vercel, IBM Cloud backend (COS + watsonx.ai), TFT model, 4 target nodes.

---

## Part 1 — The User's Perspective

GridCast has two user types. The hackathon demo is built for Type 1 (investor/judge). Type 2 (operator) is the production vision.

### Type 1: The Investor / Judge (demo target)

This is the person watching the live demo. They want to see something visually impressive that tells the story of "data centers + grids + AI weather forecasting" in 3 minutes.

**Step-by-step interaction:**

1. **Land on the app** → A dark-mode US map fills the screen. Four node markers pulse on the map: Dominion Hub (Northern Virginia), CAISO SP15 (LA), CAISO NP15 (Bay Area), ERCOT Houston.
2. **Marker color tells current stress** → Each marker is green (low stress), yellow (moderate), or red (high stress) based on its current forecast.
3. **Click a marker** → A side panel slides in with that node's data:
   - Headline number: "Recommended allocation: **41% of excess capacity, 80% confidence**"
   - 10-day forecast ribbon chart (P10/P50/P90 bands widening over time)
   - Last-7-days actual demand vs. forecast
   - Fuel mix donut (renewable vs. fossil right now)
4. **See the confidence band visually widen** → Day 1 has a thin band, Day 10 is wide. This communicates *uncertainty over time* without explanation.
5. **Click "Refresh Forecast"** → The page re-fetches the latest JSON from COS. Timestamp updates: "Updated 2 minutes ago". The chart redraws.
6. **Click "Replay"** → Map switches to historical mode. Pick one of three events:
   - **2021 Texas Winter Storm** (ERCOT Houston turns deep red)
   - **2022 Pacific Northwest Heat Dome** (CAISO NP15 stays yellow for days)
   - **2023 PJM Summer Stress** (Dominion Hub flashes red)
7. **See the "we would have predicted this" moment** → The replay shows the forecast made 72 hours before the event already had P90 in the red zone. This is the punchline of the demo.

**What the user takes away:** "GridCast can tell utilities, days ahead and node-by-node, how confident they should be in their excess capacity. That's the missing piece for flexible data center contracts."

### Type 2: The Operator (production vision, not in demo)

Same map, but with their utility's real internal data. They:
- Set custom alert thresholds (e.g., "warn me if any node's P90 exceeds 80%")
- Drill into transmission congestion components
- Export forecasts to their planning system
- See historical forecast accuracy by node and horizon

The hackathon demo *mentions* this tier in the pitch but doesn't build it.

---

## Part 2 — The Developer's Perspective

Two developers. The API contract (JSON shapes) is the only handoff. Each track works independently after fixtures are written.

### The Architecture (Option B)

```
┌──────────────┐       ┌─────────────┐       ┌──────────────┐       ┌──────────────┐
│ Open-Meteo   │       │   EIA API   │       │ Grid Status  │       │   ERA5 (CDS) │
│ (live forecast)│     │ (live demand)│      │  (live LMP)  │       │ (training only)│
└──────┬───────┘       └──────┬──────┘       └──────┬───────┘       └──────┬───────┘
       │                      │                     │                      │
       └──────────────┬───────┴─────────────────────┘                      │
                      │                                                    │
                      ▼                                                    ▼
            ┌──────────────────┐                              ┌──────────────────┐
            │  inference.py    │                              │   training.py    │
            │ (run on watsonx) │  ◄───── loads checkpoint ──  │ (run on Colab)   │
            └────────┬─────────┘                              └──────────────────┘
                     │ writes
                     ▼
            ┌──────────────────────┐
            │   IBM COS Bucket     │
            │ ┌──────────────────┐ │
            │ │ forecast_*.json  │ │
            │ │ replay_*.json    │ │
            │ │ model.ckpt       │ │
            │ └──────────────────┘ │
            └────────┬─────────────┘
                     │ reads (via Next.js API route, hides credentials)
                     ▼
            ┌──────────────────────┐
            │  Next.js on Vercel   │
            │  (React + Tailwind   │
            │   + Mapbox)          │
            └──────────────────────┘
```

### Person A — Data, ML, Backend

| Phase | What | Output | Status |
|---|---|---|---|
| 0 | Accounts + keys | `.env` filled | ✓ DONE |
| 1 | Ingestion scripts (EIA, Grid Status, Open-Meteo) | `backend/data/*.py` + 1 day of pulled real data | NEXT |
| 2 | Feature engineering | aligned hourly dataset with weather + demand + LMP | |
| 3 | TFT training on Colab T4 | `model.ckpt` uploaded to COS | |
| 4 | Inference script | `forecast_<node>.json` + `replay_<event>.json` written to COS | |
| 5 | Fixtures from real data | `frontend/src/fixtures/*.json` committed to repo | unblocks Person B |
| 6 | (optional) FastAPI on Code Engine | live refresh endpoint — only if time permits | |

### Person B — Frontend, UI

| Phase | What | Output |
|---|---|---|
| A | Next.js scaffold + Tailwind + Mapbox + Recharts | empty app shell deployed on Vercel |
| B | Map view (4 nodes, color-coded markers) | interactive map reads from `MOCK_MODE=true` fixtures |
| C | Node detail panel + forecast chart with P10/P50/P90 bands | side panel, animated open/close |
| D | Refresh button + last-updated timestamp | re-fetch from current source |
| E | Replay view (3 historical events) | event picker, map color animation over time |
| F | Polish: transitions, loading states, demo dry-run | demo-ready |
| G | Integration day: flip `MOCK_MODE=false` | reads from COS via Next.js API route |

### The Handoff Contract

The API contract is 5 endpoints. With Option B, these are mostly static JSON files at known URLs.

| Endpoint | What it returns | Source |
|---|---|---|
| `GET /api/nodes` | List of 4 nodes with metadata | static |
| `GET /api/nodes/{id}/forecast` | 10-day forecast with quantiles | `forecast_{id}.json` from COS |
| `GET /api/nodes/{id}/live` | Current state (demand, LMP, fuel mix) | `live_{id}.json` from COS |
| `POST /api/nodes/{id}/refresh` | Triggers re-read from COS | proxies to COS |
| `GET /api/replay/{event_id}` | Historical event playback data | `replay_{event_id}.json` from COS |

In Next.js, each becomes a file in `app/api/`. Each route fetches from COS server-side, hiding the COS credentials.

### The Critical Path

The shortest line from where you are now to a working demo:

```
Phase 1 (data pull) → Phase 5 (fixtures) → unblocks Person B
                  ↓
Phase 2 → Phase 3 (training) → Phase 4 (inference) → Phase G (Person B swaps to real)
```

Everything else (Phase 6 FastAPI, polish) is optional.

### What Each Person Does Today

**Person A**: Build the 3 ingestion scripts (`backend/data/eia.py`, `gridstatus.py`, `openmeteo.py`), pull 1 day of real data for the 4 nodes, and use those numbers to write the 5 fixture JSON files.

**Person B**: Scaffold Next.js + Tailwind + Mapbox, set up the project on Vercel, draft the empty page layouts. Wait for fixtures (~30 min).

After today, both work in parallel until integration day.
