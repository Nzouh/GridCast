# GridCast — Web App Spec (Frontend + Backend)

## Context

GridCast is a hackathon project (potential startup base) that visualizes a
10-day probabilistic forecast of grid stress for 4 US transmission nodes
(Dominion Hub, CAISO SP15, CAISO NP15, ERCOT Houston) and outputs a
recommended power-allocation percentage for data-centre tenants.

The team is split:
- **Teammate (Person A):** ML — finetuning / training the forecasting
  model, data pipelines, model serving.
- **User (Person B, this session):** Web app — frontend AND backend, in
  **TypeScript + Next.js** (a deviation from the design doc, which had
  React+Vite frontend and FastAPI backend).

This session's deliverable is a **detailed spec/requirements document** for
the web app, written so that:
1. Claude (design tool) can generate the UI from a precise prompt.
2. Implementation can proceed deterministically from the spec.
3. The work merges cleanly with the teammate's ML/inference work via a
   stable API contract.

The design doc (`gridcast_design.tex`) is the source of truth for: target
nodes, headline allocation formula, replay events, Tier 1 vs Tier 2
product framing, and the 5 API endpoint shapes. This spec refines the
*web* slice and reconciles it with the Next.js choice.

---

## Proposed `CLAUDE.md` for this repo (draft)

> This is the brief, persistent project memory file for future Claude
> sessions on the GridCast web app. Kept minimal — long-form spec lives
> in this plan file and (post-approval) in a `SPEC.md`.

```markdown
# GridCast — Web App

## What this repo is
GridCast is a hackathon demo + startup-base project that forecasts grid
stress for 4 US transmission nodes (Dominion Hub PJM, CAISO SP15, CAISO
NP15, ERCOT Houston) over a 10-day horizon and outputs a
recommended power-allocation % for co-located data-centre tenants.

This repo contains the **web app** (frontend + backend) in
**TypeScript + Next.js**. The ML model, training, and inference live in
a separate workstream owned by a teammate; integration happens through
a stable JSON API contract.

## Source of truth
- `gridcast_design.tex` — design doc: nodes, headline formula, replay
  events, product tiers, API endpoint shapes. Read this before making
  product decisions.
- `TEAM_SPLIT.md` — original team boundary (now superseded for the web
  half: this repo handles BE+FE, not just FE).
- `SPEC.md` — web-app spec / requirements (this session's output).

## Stack
- Next.js (App Router) + TypeScript + Tailwind
- Map: (TBD — Mapbox GL JS per design doc, candidate alternatives:
  MapLibre / react-simple-maps)
- Charts: (TBD — Recharts per design doc, candidate: Visx / Tremor)
- Mock-mode toggle via env var: web app must run end-to-end against
  local JSON fixtures with no ML backend present.

## API contract
The web backend (Next.js API routes) exposes **4 endpoints**:
- `GET /api/nodes`
- `GET /api/nodes/[id]/forecast`
- `GET /api/nodes/[id]/live`
- `GET /api/replay/[event_id]`

`POST /api/nodes/[id]/refresh` does NOT exist in this spec.
Response shapes are frozen in `SPEC.md` and `fixtures/*.json`. The
teammate's COS objects must conform to these shapes exactly.

## Working agreements
- Don't change the API contract without coordinating with the teammate.
- Never mock at component level — always go through the API layer so
  the mock/live swap is one env var.
- Replay events are pre-baked fixtures, not live inference.
```

---

## Open Questions (for brainstorming)

Tracked here so nothing slips. Will be resolved interactively with the
user before the final plan is written.

### Architecture
- **Q1. RESOLVED → App Router + RSC.** Server components fetch
  fixtures or COS server-side; client components only for map +
  interactive panel. Mock/live data source lives in a server-only
  `lib/dataSource.ts` — browser never sees the COS URL or fixture
  paths. Default for new Next.js projects.
- **Q2. RESOLVED → Option B (pre-computed forecasts from COS).**
  Teammate runs inference offline / on a schedule and writes forecast
  JSONs (per node + per replay event) to IBM Cloud Object Storage.
  Next.js reads static objects — no live Python service in the request
  path. **Consequences:**
  - Web app and ML workstreams fully decouple. Web app can ship and
    demo with zero dependency on a live Python service.
  - "Refresh Forecast" button needs new semantics (see Q12 below) —
    it cannot trigger a re-run if there is no live service.
  - Replay events fit naturally (they were always pre-baked).
  - Mock and live both look architecturally identical (object reads).
    Mock-mode = read from `/fixtures/*.json`. Live mode = read from
    COS bucket. Same JSON shape, same code path.
  - watsonx.ai / Code Engine are less prominent in the live path; the
    pitch presents them as the production upgrade path.
  - Build a fixture-fallback: if COS read fails, fall back to bundled
    fixtures so the demo never shows an error.
- **Q3. RESOLVED → TFT from scratch.** Output shape =
  5 quantiles (0.10, 0.25, 0.50, 0.75, 0.90) × 240 hourly steps per
  node, **target = demand (MW)**. The model forecasts node-level
  demand probabilistically; stress is derived UI-side from the demand
  quantiles vs a per-node threshold (`stress_threshold_demand_mw`).
  LMP is pulled and used for context visualizations (money-lost
  charts, imbalance-cost panels) but is NOT a model output.
  "Finetuning" was loose wording. Supersedes the older
  `lmp_congestion_usd` framing in the design doc.
- **Q4. RESOLVED → No DB.** Stateless web app. Reads fixtures (dev)
  or COS objects (prod). Next.js fetch cache is the only caching
  layer. Matches Option B cleanly.

### Frontend
- **Q5. RESOLVED → Mapbox GL JS via `react-map-gl`.** Public Mapbox
  token in env var. Free tier (50k loads/month) covers demo traffic.
  Polished tile-based map matches design doc.
- **Q6. RESOLVED → Visx.** D3-grade fan chart for the 5-quantile ×
  240-hour forecast. Confidence ribbons are first-class. More code
  than Recharts but the chart is the demo's hero visual; worth the
  polish budget.
- **Q7. RESOLVED → Tier 1 only.** Public US map, 4 nodes,
  click-to-panel, replay events, simulated data centres. Tier 2
  operator dashboard stays in the pitch as future work only.
- **Q8. RESOLVED → Light, clean fintech-style.** Visual reference:
  sf.atmo.ai. Whitespace-forward, restrained palette, premium SaaS
  feel. Stress colours (green/amber/red) used as accents, not
  dominant tones. Investor-friendly polish.
- **Q9. RESOLVED → Desktop-first, no mobile.** Map + side-panel
  layout assumes ≥1024px. Below that, show a "best viewed on
  desktop" notice. Demo runs on a laptop; no mobile design effort.

### Product / UX
- **Q10. RESOLVED → 2 events: Texas Winter Storm 2021 (ERCOT Houston)
  + PJM Summer 2023 (Dominion Hub).** PNW 2022 dropped — no matching
  node. Two events is enough for the story; both map cleanly to
  existing nodes. Each is one fixture file + one dropdown entry.
- **Q11. RESOLVED → 3 real-named AI hyperscaler DCs per node, with
  capacity tiers (MW) and probabilistic committed draw.**
  Use recognisable names (AWS, Google, Microsoft, Meta, Anthropic,
  NVIDIA) mapped to their known regional footprints. Each DC shows:
  - Capacity MW (large / medium / small tier)
  - Committed draw at p50 (median) = AllocationPct × capacity
  - Range ribbon: p10 (optimistic) → p90 (conservative) draw in MW
  So the probabilistic model output lands at the per-DC level.
  Proposed per-node roster (to be refined in spec):
  - Dominion Hub (NoVa): AWS Ashburn, Microsoft Azure East, Google
    Loudoun
  - CAISO SP15 (SoCal): Microsoft Azure West, Google West-LA, Meta
    Sandstone
  - CAISO NP15 (Bay Area): Google Bay-West, Meta MPK-Campus, NVIDIA
    Santa Clara
  - ERCOT Houston: Microsoft Azure TX, AWS TX-East, Google South-TX
  Legal note: these are simulated draws; add "Simulated data — for
  demonstration purposes only" disclaimer in UI footer.
- **Q12. RESOLVED → Refresh button removed.** Replaced by a
  "Forecast issued at HH:MM UTC" badge on the node panel, plus a
  small "Data sources: EIA, Open-Meteo, Grid Status — last fetched
  HH:MM" footnote. Honest about the snapshot architecture; no fake
  re-run animation.

### Integration
- **Q13. RESOLVED → Both local + COS.** `/fixtures/*.json` in repo for
  offline dev (`MOCK_MODE=true` or default when COS env unset).
  Teammate writes real JSON to COS bucket for staging/prod builds.
  Same shape both places. Open sub-question: who writes the *first*
  set of fixtures so UI work can start? (lean: user hand-writes a
  plausible synthetic set matching the frozen shapes; teammate
  overwrites with real output later.)
- **Q14. RESOLVED → No auth.** Tier 1 is a public investor view. No
  login, no API keys. Vercel default rate limiting only. Matches
  design doc.
- **Q15. RESOLVED → Vercel.** Native Next.js. Free tier, instant
  deploys. COS reads work fine from Vercel functions. Pitch
  presents IBM Code Engine as the production hosting upgrade path.

---

- **Q16. RESOLVED → Widget set: 7 components.**
  Locked: 10-day fan chart, allocation gauge, per-DC bars, US map,
  demand history (encoder window), stress timeline strip,
  ensemble spread mini-chart. Dropped: fuel mix donut, weather
  overlay on map.

---

## Final Spec

### Stack Summary

| Layer | Choice |
|---|---|
| Framework | Next.js (App Router) + TypeScript |
| Styling | Tailwind CSS |
| Map | Mapbox GL JS via `react-map-gl` (token in env) |
| Charts | Visx (D3-based, React composition) |
| Hosting | Vercel |
| Data source | IBM Cloud Object Storage (prod) / local fixtures (dev) |
| State | URL search params + RSC; no client state library |
| DB / Auth | None |

### Pages & Routes (App Router)

Single-page architecture; selected node and replay mode live in the URL.

| Route | Purpose |
|---|---|
| `/` | Landing — full US map with 4 node markers. Default state. |
| `/?node=dominion-hub` | Map + side panel for Dominion Hub. Same for `caiso-sp15`, `caiso-np15`, `ercot-houston`. |
| `/?replay=texas-2021` | Replay mode for Texas Winter Storm Uri. Map auto-focuses ERCOT Houston; panel opens with backtest data. |
| `/?replay=pjm-2023` | Replay mode for PJM Summer 2023. Auto-focuses Dominion Hub. |
| `/?node=...&replay=...` | **Precedence rule:** `replay` wins. Ignore `?node` param; use the replay event's `hero_node` as the canonical node. If `?node` value doesn't match the replay's hero node, silently redirect to `/?replay=...` (drop the `?node`). |
| `/api/nodes` | List endpoint (proxies dataSource layer). |
| `/api/nodes/[id]/forecast` | Per-node forecast endpoint. |
| `/api/nodes/[id]/live` | Per-node EIA + weather snapshot endpoint. |
| `/api/replay/[event_id]` | Pre-baked backtest endpoint. |

Notes:
- No `POST /refresh` endpoint (refresh button removed). **This spec
  governs 4 API endpoints only.** Any document referencing 5
  endpoints (including refresh) is superseded.
- API routes validate IDs against the hardcoded allowlist before any
  COS/fixture path construction (see Error Envelope above).
- API routes are thin pass-throughs around `lib/dataSource.ts`. The
  page itself can import `lib/dataSource.ts` directly in its server
  component to avoid the local API hop. The routes exist to expose a
  stable contract for the teammate and future native clients.
- `export const dynamic = 'force-dynamic'` on `page.tsx`; explicit
  `Cache-Control` headers on all API routes (see Mock-mode section).

### API Contract (frozen JSON shapes)

All shapes use ISO-8601 UTC timestamps. Quantile arrays are always
length 240 (decoder horizon). History arrays are always length 168
(encoder window). All numeric fields are SI units unless suffixed.

**`GET /api/nodes`**
```json
{
  "schema_version": 1,
  "issued_at": "2026-05-09T14:00:00Z",
  "published_at": "2026-05-09T13:55:00Z",
  "source": "cos",
  "nodes": [
    {
      "id": "dominion-hub",
      "name": "Dominion Hub",
      "iso": "PJM",
      "state": "VA",
      "ba_code": "PJM",
      "lat": 38.9, "lon": -77.0,
      "stress_level": "amber",
      "stress_probability": 0.34,
      "allocation_pct": 66
    }
  ]
}
```

**`GET /api/nodes/{id}/forecast`**
```json
{
  "node_id": "dominion-hub",
  "schema_version": 1,
  "issued_at": "2026-05-09T14:00:00Z",
  "published_at": "2026-05-09T13:55:00Z",
  "source": "cos",
  "horizon_hours": 240,
  "encoder_hours": 168,
  "quantile_levels": [0.10, 0.25, 0.50, 0.75, 0.90],
  "stress_threshold_demand_mw": 14500,
  "history": {
    "timestamps": ["2026-05-02T15:00:00Z", "..."],
    "demand_mw": [12400, 13100, "..."]
  },
  "forecast": {
    "target": "demand_mw",
    "unit": "MW",
    "timestamps": ["2026-05-09T15:00:00Z", "..."],
    "p10": [], "p25": [], "p50": [], "p75": [], "p90": []
  },
  "allocation": {
    "pct": 66,
    "pct_p50": 78,
    "pct_p10": 88,
    "p90_stress_fraction": 0.34
  },
  "stress_timeline": [
    { "hour_offset": 0, "stress_probability": 0.12, "level": "green" }
  ],
  "ensemble_spread": {
    "variable": "temperature_2m",
    "unit": "celsius",
    "timestamps": ["2026-05-09T15:00:00Z", "..."],
    "members": [[22.1, 22.3, "..."], "... 16 members ..."]
  },
  "data_centers": [
    {
      "id": "aws-ashburn",
      "name": "AWS Ashburn Campus",
      "operator": "AWS",
      "tier": "large",
      "capacity_mw": 1200,
      "committed_draw_mw": { "p10": 1080, "p50": 792, "p90": 480 }
    }
  ]
}
```

**`GET /api/nodes/{id}/live`**
```json
{
  "node_id": "dominion-hub",
  "fetched_at": "2026-05-09T14:00:00Z",
  "eia": {
    "demand_mw": 95000,
    "demand_forecast_mw": 92000,
    "demand_deviation_pct": 3.3
  },
  "weather": {
    "temperature_2m_c": 22.5,
    "wind_speed_10m_ms": 4.2,
    "ensemble_member_count": 16
  }
}
```

**Error envelope (all 4xx/5xx responses)**
```json
{
  "error": {
    "code": "NODE_NOT_FOUND",
    "message": "Node 'foo' is not a known id.",
    "source": "cos",
    "request_id": "req_abc123"
  }
}
```
Allowed node ids: `dominion-hub`, `caiso-sp15`, `caiso-np15`,
`ercot-houston`. Allowed replay ids: `texas-2021`, `pjm-2023`.
Any other value → 404 with `NODE_NOT_FOUND` / `REPLAY_NOT_FOUND`.
COS read failure (non-fallback mode) → 502 `UPSTREAM_UNAVAILABLE`.
Schema validation failure → 500 `SCHEMA_INVALID`. All errors are
logged with `request_id` for traceability.

**ID allowlisting (implemented in `lib/dataSource.ts`):**
```ts
const VALID_NODE_IDS = ['dominion-hub','caiso-sp15','caiso-np15','ercot-houston'] as const;
const VALID_REPLAY_IDS = ['texas-2021','pjm-2023'] as const;
// throw ApiError(404) before any file/URL path construction
```
Never concatenate untrusted `id` params into paths. Validate first.

**`GET /api/replay/{event_id}`**
Same shape as `/forecast` plus:
```json
{
  "event_id": "texas-2021",
  "event_name": "Texas Winter Storm Uri",
  "node_id": "ercot-houston",
  "issued_at": "2021-02-04T00:00:00Z",
  "actual_event_date": "2021-02-15T00:00:00Z",
  "narrative": "Forecast as it would have appeared on Feb 4, 2021 — 10 days before the storm peak.",
  "actuals_overlay": {
    "timestamps": ["2021-02-09T00:00:00Z", "..."],
    "demand_mw": [62100, 78400, "..."]
  }
}
```
The `actuals_overlay` enables the "look how close the p90 line came
to reality" moment, drawn over the fan chart in replay mode.

**Replay alignment rules:**
- `forecast.timestamps` and `actuals_overlay.timestamps` must share
  the same start time and 1-hour step.
- `actuals_overlay` length ≤ 240 (may be shorter if the event ended
  before the full horizon). Zod validates length ≤ 240, sorted, no
  gaps > 2h.
- Replay objects carry the same `schema_version`, `source`, and
  `published_at` envelope as normal forecasts. Freshness validation
  applies equally (replay objects never expire by age, so
  `published_at` check is skipped for replay endpoint only).

### RSC / Client Boundary Rules

These rules prevent hydration errors and non-serializable-prop crashes:
1. All props crossing the RSC→client boundary must be plain JSON:
   no `Date` objects, `Map`, class instances, functions, or
   `undefined`. Use ISO-8601 strings for timestamps everywhere;
   parse them inside client components only.
2. **Mapbox pattern (App Router–safe):** `dynamic({ ssr: false })`
   does NOT work inside Server Components. Instead, create a thin
   `MapShell` client component that holds the `dynamic()` call:
   ```ts
   // components/map/MapShell.tsx  ← 'use client'
   import dynamic from 'next/dynamic';
   const MapView = dynamic(() => import('./MapView'), { ssr: false });
   export default function MapShell(props: MapShellProps) {
     return <MapView {...props} />;
   }
   ```
   The server page renders `<MapShell>` (a client component) with
   JSON-safe props; `MapView` (Mapbox) loads only in the browser.
3. All Visx chart components are client components. They receive
   already-zipped `ForecastPoint[]` arrays as props (plain objects),
   never raw parallel arrays.
4. The `lib/dataSource.ts` module must be marked server-only
   (`import 'server-only'`) so the bundler rejects any accidental
   client-side import.

### Components

Server components (RSC) render layout and fetch data; client
components (`'use client'`) wrap interactivity.

```
app/
  layout.tsx                  (server) site shell + fonts + footer
  page.tsx                    (server) map page; reads searchParams; fetches /nodes + selected node forecast
  api/
    nodes/route.ts
    nodes/[id]/forecast/route.ts
    nodes/[id]/live/route.ts
    replay/[event_id]/route.ts
components/
  map/
    MapView.tsx               (client) Mapbox container
    NodeMarker.tsx            (client) marker w/ stress colour
  panel/
    NodePanel.tsx             (server) panel layout; receives forecast as prop
    NodePanelHeader.tsx       (server) title, stress chip, "Issued at HH:MM UTC" badge
    AllocationGauge.tsx       (client, Visx) headline % + confidence band
    FanChart.tsx              (client, Visx) 5-band quantile fan + demand history left of t=0
    StressTimeline.tsx        (client, Visx) 240h colour strip with hover tooltip
    EnsembleSpread.tsx        (client, Visx) 16-line spaghetti
    DataCenterList.tsx        (server) renders DC cards
    DataCenterCard.tsx        (server) name, tier, capacity, p10/p50/p90 bars
  controls/
    ReplaySelector.tsx        (client) dropdown: live / Texas 2021 / PJM 2023; updates URL
    LegendKey.tsx             (server) green/amber/red + p10–p90 explainer
  shell/
    SiteHeader.tsx            (server) brand, nav
    DataSourceFooter.tsx      (server) "Data: EIA, Open-Meteo, Grid Status. Simulated DC draws — for demo only."
    DesktopOnlyNotice.tsx     (server) renders below 1024px
lib/
  dataSource.ts               (server-only) fixture vs COS switch; typed reads
  types.ts                    (shared) Node, Forecast, Live, Replay, DataCenter
  formulas.ts                 (shared) AllocationPct from p90; stress level from probability
  fixtures/
    nodes.json
    forecast/{node_id}.json   × 4
    live/{node_id}.json       × 4
    replay/{event_id}.json    × 2
```

### Mock-mode Strategy

`lib/dataSource.ts` exposes typed async functions:
- `getNodes(): Promise<NodeListResponse>`
- `getForecast(id): Promise<Forecast>`
- `getLive(id): Promise<Live>`
- `getReplay(eventId): Promise<Replay>`

Behaviour controlled by env vars (read server-side only):
- `GRIDCAST_DATA_SOURCE` — `fixtures` (default) or `cos`
- `COS_BASE_URL` — public read URL of the IBM COS bucket (when source=cos)

Same TypeScript types either way. The browser bundle never sees
`COS_BASE_URL`.

**Startup validation (fail-fast):**
- If `GRIDCAST_DATA_SOURCE=cos` and `COS_BASE_URL` is not set, throw
  at module load time — not at request time. This prevents silent
  fixture mode from activating in deployed environments when env vars
  are misconfigured.
- In Vercel prod/preview, add a required env var check via
  `next.config.mjs` `env` validation block.

**Fallback policy (fail-visible, not fail-silent):**
- In `fixtures` mode: always serve fixtures. No fallback needed.
- In `cos` mode: if COS read fails, return a typed 502 error (do NOT
  silently serve fixtures). The UI renders an explicit error state.
  Emergency fixture fallback is opt-in via
  `GRIDCAST_ENABLE_FIXTURE_FALLBACK=true` only; must never be the
  default in prod; activates a "Showing cached demo data" banner.
- All reads log a structured entry: `{request_id, source, cos_key,
  etag, schema_version, published_at, age_seconds, validated,
  fallback, latency_ms}`.

**Freshness validation:**
- After schema validation, check `published_at` age. If
  `now - published_at > MAX_FORECAST_AGE_HOURS` (default: 25h),
  surface a "Data may be stale" banner in the UI panel header.
  Do not hard-fail — stale-but-valid data is still usable for demo.

**Runtime validation (Zod at data-source boundary):**
All data read from COS or fixtures is validated against Zod schemas
before being returned from `getX()`. Schema checks include:
- Array lengths: `timestamps.length === 240`, `history.timestamps.length === 168`
- `members.length === 16`, each member `length === 240`
- Finite numbers (no NaN, ±Infinity)
- Timestamps ISO-8601 UTC, sorted ascending, no gaps > 2h
- Quantile ordering: `p10 ≤ p25 ≤ p50 ≤ p75 ≤ p90` at each point
- Stress probabilities ∈ [0,1]
- Allocation pcts ∈ [0,100]
If validation fails: return `SCHEMA_INVALID` error; never pass
partially-validated data to components.

**Fan chart array zipping (in `lib/dataSource.ts`):**
After reading and validating the parallel arrays, zip them into
internal point objects once at the data-source boundary:
```ts
type ForecastPoint = { t: string; p10: number; p25: number;
                       p50: number; p75: number; p90: number };
const points: ForecastPoint[] = forecast.timestamps.map((t, i) => ({
  t, p10: forecast.p10[i], p25: forecast.p25[i], p50: forecast.p50[i],
  p75: forecast.p75[i], p90: forecast.p90[i]
}));
```
Visx `AreaClosed` receives `points` — never the raw parallel arrays.
This prevents index drift from manifesting silently in charts.

**Cache-Control:**
- `/api/nodes`: `Cache-Control: no-store` (stress levels must be fresh)
- `/api/nodes/[id]/forecast`: `Cache-Control: no-store`
- `/api/nodes/[id]/live`: `Cache-Control: s-maxage=60, stale-while-revalidate=120`
  (live snapshot; 60s server cache avoids COS fan-out on every reload)
- `/api/replay/[event_id]`: `Cache-Control: public, max-age=86400`
  (replay data is immutable)
- Next.js page: `export const dynamic = 'force-dynamic'` on `page.tsx`.

**Schema negotiation:**
- All payloads carry `schema_version: 1`. Zod schema in
  `lib/dataSource.ts` rejects any object with a `schema_version`
  it doesn't recognise with a typed `SCHEMA_VERSION_UNSUPPORTED`
  error — not a silent partial parse. When the teammate upgrades the
  schema, bump the version and update the Zod schema together.

Local dev: `GRIDCAST_DATA_SOURCE` unset → fixtures. Vercel preview /
prod: env vars set → COS. The mock/live swap is a one-line config
change in Vercel.

### Stress Colour Mapping (single source of truth)

`lib/formulas.ts`:
- `green` if `stress_probability < 0.20`
- `amber` if `0.20 ≤ stress_probability < 0.50`
- `red` if `stress_probability ≥ 0.50`

**Per-hour stress probability (derived from the demand forecast):**
```
stress_probability(h) = P(demand_h > stress_threshold_demand_mw)
```
Computed by linear interpolation of the inverse CDF defined by the
5 quantiles `[p10, p25, p50, p75, p90]`. If `threshold ≥ p90`,
extrapolate down to floor 0; if `threshold ≤ p10`, the probability
caps at 1. The model never outputs `stress_probability` directly —
it is always derived from the demand quantiles in `lib/formulas.ts`.

**`p90_stress_fraction`** = fraction of the 240-hour horizon where
`p90_demand > stress_threshold_demand_mw`.

`AllocationPct = round((1 - p90_stress_fraction) × 100)` — translates
worst-quantile stress coverage into a recommended allocation cap.

### Branding & Hero Decisions

- **Header:** "GridCast" wordmark only. No tagline.
- **Footer:** "Data: EIA, Open-Meteo, Grid Status." + "Simulated data
  centre draws — for demonstration purposes only." + "Built on IBM
  Cloud" badge (right-aligned).
- **Landing state:** Full-viewport map. No floating cards, no
  KPI strip, no marketing band. Pure tool aesthetic.
- **Click-state:** Side panel slides in from the right. Panel acts as
  the "summary card" — all per-node detail lives here, never on the
  landing surface.

### Claude-design UI Prompt (paste-ready)

> **Product:** GridCast — a probabilistic 10-day forecast of US
> electricity grid stress, designed for data-centre operators
> deciding how much load to commit to flexible contracts.
>
> **Audience for this UI:** investors and judges at a hackathon
> demo. They will see the screen for ~90 seconds. The product must
> read as serious, infrastructural, and premium — not as a
> dashboard widget.
>
> **Visual reference:** sf.atmo.ai. Clean, light, climate /
> infrastructure SaaS aesthetic. Adjacent references: Linear,
> Mercury, Stripe — restrained typography, generous whitespace,
> data-forward but premium. Avoid: Bloomberg-terminal density,
> SCADA-control-room dark themes, traditional dashboard clutter.
>
> **Stack constraints:** Next.js + TypeScript + Tailwind. Map is
> Mapbox GL JS via `react-map-gl`. All charts are Visx. Desktop-only
> (≥1024px). Below 1024px show a single centred message:
> "GridCast is best viewed on desktop." Do not design mobile layouts.
>
> ---
>
> **Page layout (single page, two states):**
>
> *Landing state:* Header with "GridCast" wordmark (left) and a
> small "Replay event ▾" dropdown (right). Below: a US map filling
> the full viewport, with 4 circular markers — Dominion Hub
> (Northern Virginia), CAISO SP15 (Los Angeles), CAISO NP15
> (San Francisco Bay), ERCOT Houston. Each marker is colour-coded:
> green / amber / red, with a subtle pulse on red. Footer at the
> bottom: data sources + "Simulated data — for demonstration
> purposes only" + "Built on IBM Cloud" badge.
>
> *Node-selected state:* Same map remains visible but shifted
> slightly left. A side panel (~420px wide, full-height) slides in
> from the right. Map markers de-emphasise except the selected
> one, which gets a focus ring.
>
> ---
>
> **Side panel content (top-to-bottom):**
>
> 1. **Header strip.** Node name in serif/grotesk display weight
>    (e.g. "Dominion Hub"). Below it, a thin meta line: ISO + state
>    + ba code (e.g. "PJM · Virginia · BA: PJM"). To the right,
>    a small chip: stress level (green "stable" / amber "elevated"
>    / red "stressed"). A close (×) button in the corner.
>
> 2. **"Forecast issued" badge.** Single small line just below the
>    header: "Forecast issued 14:00 UTC · 9 May 2026". Muted colour.
>
> 3. **Allocation gauge (hero number).** A large numeric display:
>    "66%" in display weight, ~80–100px. Subtitle: "Recommended
>    allocation". Below the number, a thin horizontal confidence
>    band labelled "p10–p90: 48% – 82%". This is the most prominent
>    element after the node name.
>
> 4. **Fan chart (the centrepiece visual).** ~280px tall. X-axis
>    spans 17 days: 7 days of past on the left (demand history line
>    in a single solid stroke), then a vertical "now" divider, then
>    10 days of forecast as 5 stacked translucent quantile bands
>    (p10–p90 outermost, p25–p75 middle, p50 darkest line). Y-axis:
>    demand in MW. A horizontal dashed line at the stress threshold
>    (e.g. 14,500 MW for Dominion zone) labelled "Stress threshold".
>    Hover reveals values at that hour. In replay mode, an additional
>    solid line draws the actual realised demand over the forecast
>    bands, ideally finishing in the p90 region for stress events.
>
> 5. **Stress timeline strip.** Just below the fan chart, full panel
>    width, ~24px tall. 240 vertical cells, one per forecast hour,
>    coloured green / amber / red by stress probability. Day boundary
>    ticks above. Hover shows the hour and stress probability.
>
> 6. **Ensemble spread mini-chart.** ~140px tall. Title: "Weather
>    ensemble (16 GFS members)". 16 thin near-transparent lines
>    (~25% opacity, 1px stroke) showing temperature over the 10-day
>    horizon. Single solid line at the ensemble mean. Y-axis in °C.
>    The visual point: lines fan apart with horizon → uncertainty grows.
>
> 7. **Data centre tenants (3 cards in a vertical stack).**
>    Each card: operator logo or initial avatar (left), name + tier
>    label (centre-left), capacity in MW (right-aligned). Below:
>    a horizontal bar showing committed draw, with a thin range
>    indicator showing p10–p90 envelope. Example for Dominion Hub:
>    "AWS Ashburn Campus · Large · 1,200 MW · committed 792 MW
>    (range 480 – 1,080 MW)". Three cards: AWS Ashburn, Microsoft
>    Azure East, Google Loudoun.
>
> 8. **Footer link.** Small "Methodology" text link (opens an info
>    drawer with the AllocationPct formula and data source
>    attribution).
>
> ---
>
> **Header — replay selector dropdown.** When a replay event is
> selected ("Texas Winter Storm Uri 2021" or "PJM Summer Heat 2023"),
> a slim banner appears under the header: "Replay mode · Forecast
> issued 4 Feb 2021, 10 days before peak. Showing what GridCast
> would have predicted." with a "Return to live" close button.
>
> ---
>
> **Theme tokens:**
> - Background: white (#FFFFFF) primary surface, very light
>   blue-grey (#F7F8FA) for panel surface.
> - Text: near-black (#0B0F19) primary, medium grey (#6B7280)
>   secondary, light grey (#9CA3AF) tertiary.
> - Accents: a single brand colour (suggest deep teal / navy
>   #0F3D56) for links and the wordmark.
> - Stress colours (used sparingly, only for stress states):
>   green #16A34A, amber #F59E0B, red #DC2626. Use 15% tinted
>   backgrounds for chips, full saturation for the small status dots.
> - Quantile bands on fan chart: monochromatic teal at varying
>   opacity (p10–p90 outermost ~12%, p25–p75 ~28%, p50 line at 100%).
>   Avoid rainbow palettes.
> - Typography: a modern grotesk for body (Inter / Geist / similar);
>   the same family in display weight for the wordmark and the
>   allocation hero number. No serifs.
> - Spacing: generous. Match the airy density of Linear / sf.atmo.ai.
>
> ---
>
> **What NOT to design:**
> - No mobile layouts.
> - No dark mode.
> - No login / signup / waitlist.
> - No fuel mix donut, no weather raster overlay.
> - No "Refresh forecast" button. Forecasts are snapshots; the
>   timestamp badge is the only freshness indicator.
> - No fictional dashboard widgets beyond the seven listed.
>
> **Data realism note:** The actual forecast values are produced by
> a separate ML model. Use plausible placeholder demand values in
> mockups, scaled per node (Dominion zone p50 ~12–18 GW, CAISO SP15
> ~15–25 GW, CAISO NP15 ~10–15 GW, ERCOT Houston zone ~10–17 GW).
> Allocation 60–80% in green states, 20–40% in red states. Do not
> invent additional data fields beyond those listed.

### Verification

End-to-end checks before declaring the web app done.

**Local dev (mock mode, no COS, no teammate dependency):**
1. `pnpm install && pnpm dev` boots Next.js on :3000.
2. `/` renders the US map with all 4 markers visible and
   colour-coded per `fixtures/nodes.json`.
3. Clicking each marker opens the side panel; URL updates to
   `?node=...`. All seven widgets render with non-zero data.
4. The fan chart shows 7 days of past demand joining smoothly to the
   forecast bands at t=0.
5. The stress timeline strip has 240 cells.
6. The ensemble spread shows 16 distinct lines.
7. Each DC card shows a numeric committed-draw bar with the
   p10–p90 range visible.
8. Replay selector → "Texas Winter Storm Uri 2021" auto-focuses
   ERCOT Houston, replay banner appears, fan chart shows the
   `actuals_overlay` line landing in the upper quantiles.
9. Replay → "PJM Summer 2023" auto-focuses Dominion Hub.
10. Resize browser <1024px → desktop-only notice renders.

**Type & lint:**
- `pnpm tsc --noEmit` passes.
- `pnpm lint` passes.
- All API route handlers have typed responses matching `lib/types.ts`.
- All four `getX` functions in `lib/dataSource.ts` round-trip the
  same JSON shape regardless of source (fixtures vs COS).

**Production parity (post-deploy):**
- Set `GRIDCAST_DATA_SOURCE=cos` and `COS_BASE_URL=...` on Vercel
  preview. Page loads identical to mock mode (same shapes, same
  components, just different bytes).
- Kill COS access (e.g. break the URL) → API returns 502
  `UPSTREAM_UNAVAILABLE`; UI shows an explicit error state. No
  silent fixture fallback unless `GRIDCAST_ENABLE_FIXTURE_FALLBACK=true`.
- Set `GRIDCAST_DATA_SOURCE=cos` without `COS_BASE_URL` → app fails
  to start (startup validation), not at request time.
- Mapbox token configured via `NEXT_PUBLIC_MAPBOX_TOKEN`.
- Lighthouse desktop score ≥ 90 on `/` and `/?node=dominion-hub`.

**Teammate handoff:**
- API contract document = the "API Contract" section of this spec.
- Teammate's COS bucket structure must match the `fixtures/` tree
  (`forecast/{node_id}.json`, `live/{node_id}.json`,
  `replay/{event_id}.json`, plus `nodes.json`).
- Integration day = set Vercel env vars + smoke-test all four nodes
  + both replays. Should be < 30 minutes if shapes match.

---

## Critical files to be created (greenfield)

This is a new web app — no existing code to reuse. All paths
relative to repo root.

- `app/layout.tsx`, `app/page.tsx`
- `app/api/nodes/route.ts`
- `app/api/nodes/[id]/forecast/route.ts`
- `app/api/nodes/[id]/live/route.ts`
- `app/api/replay/[event_id]/route.ts`
- `components/map/MapView.tsx`, `components/map/NodeMarker.tsx`
- `components/panel/NodePanel.tsx`, `NodePanelHeader.tsx`,
  `AllocationGauge.tsx`, `FanChart.tsx`, `StressTimeline.tsx`,
  `EnsembleSpread.tsx`, `DataCenterList.tsx`, `DataCenterCard.tsx`
- `components/controls/ReplaySelector.tsx`, `LegendKey.tsx`
- `components/shell/SiteHeader.tsx`, `DataSourceFooter.tsx`,
  `DesktopOnlyNotice.tsx`
- `lib/dataSource.ts`, `lib/types.ts`, `lib/formulas.ts`
- `fixtures/nodes.json`
- `fixtures/forecast/{dominion-hub,caiso-sp15,caiso-np15,ercot-houston}.json`
- `fixtures/live/{...}.json` (4 files)
- `fixtures/replay/{texas-2021,pjm-2023}.json`
- `tailwind.config.ts`, `next.config.mjs`, `package.json`,
  `tsconfig.json`, `.env.example`
- `CLAUDE.md` (per draft above)
- `SPEC.md` (this spec, distilled)

## Reconciliation with teammate's commit `7c4b158` ("Adding backend")

Teammate has shipped `backend/fixtures/generate.py` + 16 JSON
fixtures + `DESIGN_WALKTHROUGH.md`. Their shapes diverge from this
spec. Decision: **we hold the spec; teammate regenerates.** The
list below is the diff `generate.py` needs to match this spec.

| # | Field / behaviour | Teammate currently | Spec requires | Notes for teammate |
|---|---|---|---|---|
| 1 | Node IDs | `dominion_hub`, `caiso_sp15`, `caiso_np15`, `ercot_houston` (snake_case) | `dominion-hub`, `caiso-sp15`, `caiso-np15`, `ercot-houston` (kebab-case) | URL-friendly; matches Next.js dynamic route segments. Affects file names + `id` fields. |
| 2 | Forecast target variable | `stress` ∈ [0,1] (primary) + `demand_mw` (secondary) per-point | `demand_mw` quantile arrays in `forecast.{p10,…,p90}` (target = node demand in MW) | Stress level is **derived UI-side** from demand quantiles vs `stress_threshold_demand_mw`. LMP is no longer a model target; it's pulled for context visualizations only (money-lost / imbalance-cost charts). |
| 3 | Forecast point structure | `points: [{timestamp, horizon_hours, stress: {p10, p25, p50, p75, p90}, demand_mw: {p10, p50, p90}}]` | Parallel arrays: `forecast.timestamps[]`, `forecast.p10[]`, `forecast.p25[]`, `forecast.p50[]`, `forecast.p75[]`, `forecast.p90[]` | More compact; faster to ingest in Visx. |
| 4 | Encoder history location | `live_<id>.json.last_7_days` with `actual_demand_mw` / `forecast_demand_mw` | `forecast_<id>.json.history` with `timestamps[]` + `demand_mw[]` (length 168) | Past demand belongs with the forecast; `/live` is purely the current snapshot. |
| 5 | `/live` payload | demand_mw + lmp_usd_per_mwh + fuel_mix (7 keys) + current_stress + last_7_days | `eia: {demand_mw, demand_forecast_mw, demand_deviation_pct}` + `weather: {temperature_2m_c, wind_speed_10m_ms, ensemble_member_count}` | No fuel mix (widget dropped). No history (moved to `/forecast`). Add weather snapshot. |
| 6 | Refresh endpoint | `POST /refresh` + `refresh_response.json` exists | **Removed.** No fixture, no route. | Replaced by `issued_at` field on `/forecast`. UI shows "Forecast issued at HH:MM UTC". |
| 7 | Replay events count | 3 events including `pnw_heat_dome_2022` | 2 events: `texas-2021` (was `texas_winter_2021`), `pjm-2023` (was `pjm_summer_2023`). PNW dropped. | PNW has no matching node. |
| 8 | Stress thresholds | `< 0.40` green, `0.40–0.70` yellow, `> 0.70` red, baked into `stress_level` field | UI computes from `stress_probability`: `< 0.20` green, `0.20–0.50` amber, `≥ 0.50` red. **Remove** `stress_level` strings from all fixtures. | Single source of truth in `lib/formulas.ts`. Easier to retune. |
| 9 | Stress level label | `"yellow"` | `"amber"` | UI-side only after #8. |
| 10 | Allocation block | `{percent, confidence, horizon_days}` | `{pct, p90_stress_fraction}` | No `confidence` field (not defined in design doc). UI builds display string. |
| 11 | **MISSING — ensemble_spread** | not present | Add `ensemble_spread: {variable, unit, timestamps[240], members[16][240]}` to each `forecast_<id>.json` | Source: Open-Meteo Ensemble API (16 GFS members) per design doc Appendix. |
| 12 | **MISSING — data_centers** | not present | Add `data_centers: [{id, name, operator, tier, capacity_mw, committed_draw_mw: {p10, p50, p90}}]` (3 entries) to each `forecast_<id>.json` | Per-node rosters listed in Q11 resolution above (AWS Ashburn, etc.). `committed_draw_mw.p50 = capacity_mw × allocation.pct / 100`; p10/p90 use the corresponding stress fraction at p10/p90. |
| 13 | Fixture file layout | `backend/fixtures/out/<flat>` | `fixtures/nodes.json`, `fixtures/forecast/<id>.json`, `fixtures/live/<id>.json`, `fixtures/replay/<event_id>.json` | Symlink or move; move/symlink note in their README acknowledges this is Person B's call. |
| 14 | `DESIGN_WALKTHROUGH.md` "dark-mode US map" | Walkthrough mentions dark mode | UI is **light fintech** (sf.atmo.ai) | Walkthrough is descriptive; fixtures don't enforce. Either update walkthrough or note as superseded. |
| 15 | Fan chart axis | (implicit) stress 0–1 | demand MW, with horizontal dashed `stress_threshold_demand_mw` line | Follows from #2. The threshold line is the visual "danger zone" cutoff. |
| 16 | **COS publication must be atomic** | not specified | Publish to an immutable versioned prefix (e.g. `v/{timestamp}/`), then flip a single `active.json` manifest pointing to the prefix only after all objects pass a checksum check. Web app reads from `active.json` to resolve the prefix. | Prevents the UI from reading a mixed state (new `nodes.json` + old `forecast_*.json`). |
| 17 | **Allocation quantile formulas (committed_draw_mw — single source of truth)** | `committed_draw_mw.p50 = capacity × alloc.percent/100` only | **Teammate pre-computes all three** committed_draw values in the fixture using: `pct_p10 = round((1 − p10_stress_fraction) × 100)`, `pct_p50 = round((1 − p50_stress_fraction) × 100)`, `pct = round((1 − p90_stress_fraction) × 100)`. Fixture includes `committed_draw_mw: {p10, p50, p90}` directly. UI reads and displays; no re-derivation in UI. `allocation.pct_p10` and `allocation.pct_p50` are also kept in the fixture for panel display. | Removes dual-derivation ambiguity; teammate owns the formula implementation once. |

## Changelog

### Round 2 — Security and data-integrity review (claudex 20260510-002216-117408)

**Taken (HIGH):**
- Added `"source"` field to all API responses. Surfaced whether data
  came from COS or fixtures; enables UI stale/mock banner.
- Replaced silent fixture fallback with fail-visible policy: `cos`
  mode returns a typed error on COS failure; `GRIDCAST_ENABLE_FIXTURE_FALLBACK`
  is an explicit opt-in only. Prevents stale synthetic data appearing
  as live production truth.
- Added ID allowlist enforcement in `lib/dataSource.ts` before any
  path construction. Prevents path traversal, object probing, and
  cache poisoning via crafted `?node=` or `?replay=` params.
- Added Zod runtime schema validation at the data-source boundary
  (array lengths, finite numbers, sorted timestamps, quantile
  ordering, probability ranges). TypeScript types alone don't catch
  malformed COS bytes.

**Taken (MEDIUM):**
- Added `export const dynamic = 'force-dynamic'` to `page.tsx` and
  explicit `Cache-Control` headers to all API routes to prevent RSC
  and CDN caching from serving stale forecast data.
- Added RSC/client boundary rules section: `Date` → ISO strings,
  `MapView` behind `dynamic({ ssr: false })`, Visx receives
  pre-zipped point objects, `lib/dataSource.ts` marked server-only.
- Added Error Envelope shape (`code`, `message`, `source`,
  `request_id`) and status-code rules for all 4xx/5xx paths.
- Added fan chart parallel-array zipping in `lib/dataSource.ts`:
  arrays are zipped to `ForecastPoint[]` once at the boundary;
  Visx never receives raw parallel arrays.
- Added URL precedence rule: `?replay` wins over `?node`; incompatible
  `?node` silently redirected to canonical replay node.
- Added allocation quantile fields (`pct_p10`, `pct_p50`) to
  `/forecast` response and formulas for `committed_draw_mw.p10/p90`.
  Closes the gap where teammate had no spec for computing DC draw bands.
- Fixed `CLAUDE.md` draft to say 4 endpoints (removed `POST /refresh`).
- Added reconciliation row #16 (atomic COS publication via versioned
  prefix + `active.json` manifest pointer) and row #17 (allocation
  quantile formulas).

**Taken (LOW):**
- Added structured log requirement (`request_id`, `source`,
  `cos_key`, `etag`, `validated`, `fallback`, `latency_ms`) to
  Mock-mode Strategy.

### Round 3 — Ops and SRE review (claudex 20260510-002216-117408)

**Taken (HIGH):**
- Added `published_at` + `schema_version` to all API payloads.
  Added freshness validation in `lib/dataSource.ts`: if
  `now - published_at > 25h`, surface a "Data may be stale" banner
  (warn, don't hard-fail).
- Added `active.json` manifest pointer (row #16 in reconciliation)
  and `schema_version` negotiation: unknown schema version returns
  typed `SCHEMA_VERSION_UNSUPPORTED` error, not a silent partial parse.
- Added startup validation: `GRIDCAST_DATA_SOURCE=cos` without
  `COS_BASE_URL` throws at module load, not at request time. Updated
  verification test: COS failure → 502, not silent fixture fallback.
- Fixed the `dynamic({ ssr: false })` pattern: moved it into a
  `MapShell` client component wrapper so the Server Component page
  never directly calls `dynamic()`. This is required by Next.js App
  Router.

**Taken (MEDIUM):**
- Changed `/api/nodes/[id]/live` cache to `s-maxage=60, stale-while-revalidate=120`
  to prevent COS fan-out on every reload without serving truly stale
  live snapshots.
- Added replay alignment rules: `actuals_overlay` timestamps aligned
  with `forecast.timestamps`, Zod validates length ≤ 240, sorted, same
  schema envelope; freshness check skipped for replay endpoint.
- Resolved allocation inconsistency: teammate pre-computes all three
  `committed_draw_mw` values; UI reads and displays them as-is. No
  dual-derivation. Updated reconciliation row #17.

**Rejected (MEDIUM):**
- "Define alerting, metrics, health check, runbook" — out of scope
  for a hackathon demo. Vercel built-in log drain + structured logs
  already specified are sufficient.
- "Support one previous schema version" — schema_version=1 is the
  only version at launch. Backwards compatibility is a production
  concern; add in v2.

**Rejected (LOW):**
- "Break handoff into explicit tasks with owners" — project
  management, not spec content. The reconciliation table already
  enumerates teammate deliverables.

**Rejected:**
- "Add a diagnostics endpoint or footer metadata for demo operators"
  (LOW): out of scope for hackathon; console logs are sufficient if
  structured correctly; a diagnostics route adds attack surface.
- "Restrict Mapbox token by domain in Mapbox dashboard": this is a
  Mapbox dashboard configuration step, not a code spec item. Added
  to `.env.example` documentation only.

## Out of scope (explicit non-goals)

- Tier 2 operator dashboard.
- Mobile layouts.
- Live inference / `POST /refresh`.
- Fuel mix donut, weather raster overlay.
- Authentication, user accounts, waitlist.
- Database of any kind.
- Pacific Northwest 2022 replay event.
