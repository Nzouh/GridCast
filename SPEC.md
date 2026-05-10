# GridCast Web App — Specification

> Authoritative implementation spec. Generated from brainstorming session +
> 3-round claudex adversarial review (20260510-002216-117408).
> For decision history see `PLAN.md`. For project context see `CLAUDE.md`.

---

## Stack

| Layer | Choice |
|---|---|
| Framework | Next.js (App Router) + TypeScript |
| Styling | Tailwind CSS |
| Map | Mapbox GL JS via `react-map-gl` |
| Charts | Visx (D3-based, React composition) |
| Hosting | Vercel |
| Data source | IBM Cloud Object Storage (prod) / `fixtures/` (dev) |
| State | URL search params + RSC; no client state library |
| DB / Auth | None |

---

## Pages & Routes

Single-page app. Selected node and replay mode live in the URL.

| Route | Purpose |
|---|---|
| `/` | Landing — full US map, 4 live stress-coloured markers (filter defaults to `target`), no panel. |
| `/?filter=all` | Map shows all 20 nodes (4 live + 16 synthetic demo nodes). |
| `/?node=dominion-hub` | Map + node side panel. Valid ids: any `VALID_NODE_IDS` entry (live or synthetic). |
| `/?replay=texas-2021` | Replay mode. Auto-focuses ERCOT Houston. Filter UI hidden; map shows live nodes only. |
| `/?replay=pjm-2023` | Replay mode. Auto-focuses Dominion Hub. Filter UI hidden; map shows live nodes only. |
| `/?node=...&replay=...` | `replay` wins; `?node` is ignored. If they conflict, redirect to `/?replay=...`. |
| `/api/nodes` | Node list endpoint. |
| `/api/nodes/[id]/forecast` | Per-node forecast. Accepts any id in `VALID_NODE_IDS`. |
| `/api/nodes/[id]/live` | Per-node EIA + weather snapshot. Accepts any id in `VALID_NODE_IDS`. |
| `/api/replay/[event_id]` | Pre-baked backtest. Accepts only ids in `VALID_REPLAY_IDS`. |

**No `POST /api/nodes/[id]/refresh`** — refresh button removed.
`export const dynamic = 'force-dynamic'` on `app/page.tsx`.

---

## API Contract

All shapes use ISO-8601 UTC timestamps. Quantile arrays length 240.
History arrays length 168. Numeric fields SI unless suffixed.

### `GET /api/nodes`

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
      "lat": 38.9,
      "lon": -77.0,
      "stress_probability": 0.34,
      "allocation_pct": 66,
      "is_live": true
    }
  ]
}
```

`stress_level` is computed UI-side from `stress_probability` via
`lib/formulas.ts` — it is NOT present in the fixture.

`is_live` is `true` for the 4 production nodes the model actively
forecasts and `false` for the 16 synthetic demo nodes shipped to make
the map look credible. Both kinds use identical payload shapes and
identical visual treatment in the UI; the distinction is exposed only
through the **Target Grids** filter in the header (default on → live
only, off → all nodes).

### `GET /api/nodes/[id]/forecast`

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
    "timestamps": ["2026-05-02T15:00:00Z"],
    "demand_mw": [12400]
  },
  "forecast": {
    "target": "demand_mw",
    "unit": "MW",
    "timestamps": ["2026-05-09T15:00:00Z"],
    "p10": [],
    "p25": [],
    "p50": [],
    "p75": [],
    "p90": []
  },
  "allocation": {
    "pct": 66,
    "pct_p50": 78,
    "pct_p10": 88,
    "p90_stress_fraction": 0.34
  },
  "stress_timeline": [
    { "hour_offset": 0, "stress_probability": 0.12 }
  ],
  "ensemble_spread": {
    "variable": "temperature_2m",
    "unit": "celsius",
    "timestamps": ["2026-05-09T15:00:00Z"],
    "members": [[22.1, 22.3]]
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

**Notes:**
- `stress_timeline` has no `level` string — UI derives from `stress_probability`.
- `stress_probability` is derived from the five demand quantiles by linearly
  interpolating the inverse CDF at the per-node `stress_threshold_demand_mw`,
  then returning `P(demand_mw > threshold)`.
- `data_centers.committed_draw_mw` is pre-computed by the teammate:
  `p90 = capacity × pct/100`, `p50 = capacity × pct_p50/100`,
  `p10 = capacity × pct_p10/100`. UI reads and displays; no re-derivation.

### `GET /api/nodes/[id]/live`

```json
{
  "node_id": "dominion-hub",
  "schema_version": 1,
  "fetched_at": "2026-05-09T14:00:00Z",
  "source": "cos",
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

### `GET /api/replay/[event_id]`

Same shape as `/forecast`, plus:

```json
{
  "event_id": "texas-2021",
  "event_name": "Texas Winter Storm Uri",
  "node_id": "ercot-houston",
  "issued_at": "2021-02-04T00:00:00Z",
  "actual_event_date": "2021-02-15T00:00:00Z",
  "narrative": "Forecast as it would have appeared on Feb 4, 2021 — 10 days before the storm peak.",
  "actuals_overlay": {
    "timestamps": ["2021-02-09T00:00:00Z"],
    "demand_mw": [16200, 17800]
  }
}
```

`actuals_overlay` timestamps align with `forecast.timestamps` (same start,
1-hour step, length ≤ 240). Freshness check skipped for replay endpoint.

### Error Envelope

All 4xx/5xx responses:

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

| Code | Status | Trigger |
|---|---|---|
| `NODE_NOT_FOUND` | 404 | Unknown node id |
| `REPLAY_NOT_FOUND` | 404 | Unknown replay id |
| `UPSTREAM_UNAVAILABLE` | 502 | COS read failure in `cos` mode |
| `SCHEMA_INVALID` | 500 | Zod validation failure |
| `SCHEMA_VERSION_UNSUPPORTED` | 500 | Unknown `schema_version` |

### ID Allowlists

Validated in `lib/dataSource.ts` **before** any path construction.
Live and synthetic ids are kept in disjoint tuples and unioned for the
public allowlist:

```ts
const VALID_LIVE_NODE_IDS = [
  'dominion-hub','caiso-sp15','caiso-np15','ercot-houston',
] as const;
const VALID_SYNTHETIC_NODE_IDS = [
  'miso-indiana-hub','miso-illinois-hub','spp-north-hub','spp-south-hub',
  'nyiso-zone-j','nyiso-zone-a','iso-ne-mass-hub','pjm-western-hub',
  'pjm-aep-dayton','ercot-north','ercot-west','caiso-zp26',
  'bpa-pnw','duke-carolinas','tva-tennessee','fpl-florida',
] as const;
const VALID_NODE_IDS   = [...VALID_LIVE_NODE_IDS, ...VALID_SYNTHETIC_NODE_IDS] as const;
const VALID_REPLAY_IDS = ['texas-2021','pjm-2023'] as const;
```

`/api/nodes/[id]/{forecast,live}` accept any id in `VALID_NODE_IDS`.
`/api/replay/[event_id]` accepts only `VALID_REPLAY_IDS`. Replay focus
nodes are guaranteed to be in `VALID_LIVE_NODE_IDS`.

---

## RSC / Client Boundary Rules

1. All props crossing RSC→client boundary must be plain JSON. No `Date`
   objects, `Map`, class instances, or `undefined`. Timestamps are ISO-8601
   strings; parse them inside client components only.

2. **Mapbox — App Router–safe pattern.** `dynamic({ ssr: false })` does not
   work in Server Components. Use a `'use client'` wrapper:
   ```ts
   // components/map/MapShell.tsx  ('use client')
   import dynamic from 'next/dynamic';
   const MapView = dynamic(() => import('./MapView'), { ssr: false });
   export default function MapShell(props: MapShellProps) {
     return <MapView {...props} />;
   }
   ```
   Server page renders `<MapShell>` with JSON-safe props.

3. All Visx components are client components. They receive pre-zipped
   `ForecastPoint[]` arrays, never raw parallel arrays.

4. `lib/dataSource.ts` must be marked `import 'server-only'`.

---

## Component Tree

```
app/
  layout.tsx                    server — shell, fonts, footer
  page.tsx                      server — reads searchParams, fetches data
  api/
    nodes/route.ts
    nodes/[id]/forecast/route.ts
    nodes/[id]/live/route.ts
    replay/[event_id]/route.ts

components/
  map/
    MapShell.tsx                client — dynamic() wrapper (ssr:false)
    MapView.tsx                 client — Mapbox GL JS container
    NodeMarker.tsx              client — stress-coloured marker + pulse
  panel/
    NodePanel.tsx               server — panel layout, passes data down
    NodePanelHeader.tsx         server — name, ISO/BA meta, stress chip,
                                         "Forecast issued HH:MM UTC" badge
    AllocationGauge.tsx         client (Visx) — hero %, p10–p90 band
    FanChart.tsx                client (Visx) — 5-band fan + 7d history
    StressTimeline.tsx          client (Visx) — 240h colour strip
    EnsembleSpread.tsx          client (Visx) — 16-line spaghetti
    DataCenterList.tsx          server — 3 DC cards
    DataCenterCard.tsx          server — name, tier, MW, draw bars
  controls/
    ReplaySelector.tsx          client — dropdown, updates URL
    LegendKey.tsx               server — stress colour + band explainer
  shell/
    SiteHeader.tsx              server — "GridCast" wordmark + replay dropdown
    DataSourceFooter.tsx        server — data attribution + IBM badge
                                         + "Simulated draws" disclaimer
    DesktopOnlyNotice.tsx       server — shown below 1024px
    StaleBanner.tsx             client — shown when published_at > 25h

lib/
  dataSource.ts                 server-only — source switch + Zod
  types.ts                      shared — all TS types
  formulas.ts                   shared — stressLevel(), allocationPct()
  schemas.ts                    server-only — Zod schemas

fixtures/
  nodes.json
  forecast/
    dominion-hub.json
    caiso-sp15.json
    caiso-np15.json
    ercot-houston.json
  live/
    dominion-hub.json
    caiso-sp15.json
    caiso-np15.json
    ercot-houston.json
  replay/
    texas-2021.json
    pjm-2023.json
```

---

## Widgets in the Node Panel

| Widget | Component | Role |
|---|---|---|
| Allocation gauge | `AllocationGauge` | Hero number — "the answer" |
| Fan chart + demand history | `FanChart` | Centrepiece — what + why |
| Stress timeline strip | `StressTimeline` | At-a-glance — when |
| Ensemble spread | `EnsembleSpread` | Methodology — uncertainty source |
| Data centre cards | `DataCenterList` + `DataCenterCard` | Application — what it means |

Dropped (not in scope): fuel mix donut, weather raster overlay, refresh button.

---

## Data Centre Rosters (per node)

| Node | DC 1 | DC 2 | DC 3 |
|---|---|---|---|
| Dominion Hub (NoVa) | AWS Ashburn Campus — 1,200 MW | Microsoft Azure East — 800 MW | Google Loudoun — 650 MW |
| CAISO SP15 (SoCal) | Microsoft Azure West — 500 MW | Google West-LA — 400 MW | Meta Sandstone — 350 MW |
| CAISO NP15 (Bay Area) | Google Bay-West — 600 MW | Meta MPK Campus — 500 MW | NVIDIA Santa Clara — 300 MW |
| ERCOT Houston | Microsoft Azure TX — 700 MW | AWS TX-East — 550 MW | Google South-TX — 450 MW |

Tiers: ≥ 700 MW → large, 400–699 MW → medium, < 400 MW → small.
Committed draw pre-computed by teammate. Footer: "Simulated data — for demonstration purposes only."

---

## Mock-mode / Data Source Strategy

### Env vars

| Var | Values | Notes |
|---|---|---|
| `GRIDCAST_DATA_SOURCE` | `fixtures` (default) / `cos` | Server-side only |
| `COS_BASE_URL` | COS public read URL | Required when source=cos |
| `GRIDCAST_ENABLE_FIXTURE_FALLBACK` | `true` / unset | Emergency opt-in only |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | Mapbox token | Public |

### Startup validation

If `GRIDCAST_DATA_SOURCE=cos` and `COS_BASE_URL` is unset → throw at module
load time (not at request time). Checked in `next.config.mjs` env block.

### Fallback policy (fail-visible)

- `fixtures` mode: always serve `fixtures/`. No fallback.
- `cos` mode, COS failure: return 502 `UPSTREAM_UNAVAILABLE`. UI shows error
  state. No silent fixture serving.
- Emergency fallback (`GRIDCAST_ENABLE_FIXTURE_FALLBACK=true`): serves
  fixtures + shows "Showing cached demo data" banner. Never default in prod.

### Freshness

After Zod validation, if `now − published_at > 25h`, show `<StaleBanner>`.
Warn, don't fail — stale-but-valid data is usable for demo.

### Zod validation (at data-source boundary)

All reads validated before returning from `getX()`:
- `timestamps.length === 240` (forecast), `=== 168` (history)
- `members.length === 16`, each member length === 240
- All numbers finite (no NaN, ±Infinity)
- Timestamps ISO-8601 UTC, sorted ascending, no gap > 2h
- Quantile ordering: `p10 ≤ p25 ≤ p50 ≤ p75 ≤ p90` at each point
- Stress probabilities ∈ [0,1], allocation pcts ∈ [0,100]
- `schema_version` must equal 1; anything else → `SCHEMA_VERSION_UNSUPPORTED`

### Fan chart array zipping

Immediately after validation, zip parallel arrays into point objects:

```ts
type ForecastPoint = { t: string; p10: number; p25: number;
                       p50: number; p75: number; p90: number };
const points: ForecastPoint[] = forecast.timestamps.map((t, i) => ({
  t, p10: forecast.p10[i], p25: forecast.p25[i], p50: forecast.p50[i],
  p75: forecast.p75[i], p90: forecast.p90[i],
}));
```

Visx receives `points`, never raw parallel arrays.

### Cache-Control headers

| Route | Header |
|---|---|
| `/api/nodes` | `no-store` |
| `/api/nodes/[id]/forecast` | `no-store` |
| `/api/nodes/[id]/live` | `s-maxage=60, stale-while-revalidate=120` |
| `/api/replay/[event_id]` | `public, max-age=86400` |

---

## Stress Colour Mapping (`lib/formulas.ts`)

```ts
function stressLevel(p: number): 'green' | 'amber' | 'red' {
  if (p < 0.20) return 'green';
  if (p < 0.50) return 'amber';
  return 'red';
}

function allocationPct(p90StressFraction: number): number {
  return Math.round((1 - p90StressFraction) * 100);
}
```

Single source of truth. No `stress_level` strings in fixtures.

---

## Branding & Theme

- **Header:** "GridCast" wordmark (left) + replay selector (right). No tagline.
- **Footer:** "Data: EIA, Open-Meteo, Grid Status." + "Simulated data centre
  draws — for demonstration purposes only." + "Built on IBM Cloud" badge.
- **Landing:** Full-viewport map, no cards, no KPI strip. Pure tool.
- **Click-state:** Side panel (~420px) slides in from right.
- **Desktop-only:** Below 1024px → centred message "GridCast is best viewed on desktop."
- **No dark mode, no mobile layouts, no auth, no refresh button.**

### Theme tokens

| Token | Value |
|---|---|
| Surface | `#FFFFFF` primary, `#F7F8FA` panel |
| Text | `#0B0F19` primary, `#6B7280` secondary, `#9CA3AF` tertiary |
| Brand | `#0F3D56` (deep teal) — wordmark + links |
| Green | `#16A34A` (stress: stable) |
| Amber | `#F59E0B` (stress: elevated) |
| Red | `#DC2626` (stress: stressed) |
| Fan bands | Monochromatic teal: p10–p90 ~12% opacity, p25–p75 ~28%, p50 100% |
| Typography | Inter or Geist, no serifs |

Visual reference: **sf.atmo.ai**. Adjacent: Linear, Mercury, Stripe.

---

## Claude-design Prompt (paste-ready)

**Product:** GridCast — a probabilistic 10-day forecast of US electricity grid stress, designed for data-centre operators deciding how much load to commit to flexible contracts.

**Audience:** investors and judges at a hackathon demo (~90 seconds of screen time). Must read as serious, infrastructural, and premium — not a dashboard widget.

**Visual reference:** sf.atmo.ai. Adjacent: Linear, Mercury, Stripe — restrained typography, generous whitespace, data-forward but premium. Avoid: Bloomberg-terminal density, SCADA dark themes, traditional dashboard clutter.

**Stack:** Next.js + TypeScript + Tailwind. Map = Mapbox GL JS via react-map-gl. Charts = Visx. Desktop-only (≥1024px). Below 1024px: centred message "GridCast is best viewed on desktop."

---

**Page layout — two states:**

*Landing state:* Header with "GridCast" wordmark (left) and "Replay event ▾" dropdown (right). Full-viewport US map with 4 circular markers: Dominion Hub (Northern Virginia), CAISO SP15 (Los Angeles), CAISO NP15 (San Francisco Bay), ERCOT Houston. Markers: green / amber / red, with subtle pulse on red. Footer: data sources + "Simulated data — for demonstration purposes only" + "Built on IBM Cloud" badge.

*Node-selected state:* Map shifts slightly left. Side panel (~420px, full-height) slides in from right. Non-selected markers de-emphasise; selected marker gets focus ring.

---

**Side panel (top-to-bottom):**

1. **Header strip.** Node name in display weight. Below: "PJM · Virginia · BA: PJM" meta line. Right: stress chip (green "stable" / amber "elevated" / red "stressed"). Close (×) button.

2. **"Forecast issued" badge.** Single muted line: "Forecast issued 14:00 UTC · 9 May 2026".

3. **Allocation gauge (hero).** Large "66%" in display weight (~80–100px). Subtitle: "Recommended allocation". Below: thin confidence band "p10–p90: 48% – 82%".

4. **Fan chart.** ~280px tall. X-axis spans 17 days: 7 days of past demand (solid line, left of "now" divider) + 10 days of forecast (5 stacked translucent teal bands, p50 darkest). Y-axis: node demand in MW. Horizontal dashed line at stress threshold labelled "Stress threshold". Hover reveals hourly values. In replay mode: additional solid line of actual realised demand over the bands.

5. **Stress timeline strip.** ~24px tall, full panel width. 240 cells (one per forecast hour), coloured green/amber/red by stress probability. Day ticks above. Hover: hour + probability.

6. **Ensemble spread mini-chart.** ~140px tall. Title: "Weather ensemble (16 GFS members)". 16 thin lines (~25% opacity, 1px) for temperature. Solid mean line. Y-axis in °C. Lines fan apart with horizon.

7. **Data centre cards (3, vertical stack).** Each: operator initial avatar (left) + name + tier (centre) + capacity MW (right). Below: horizontal committed-draw bar with p10–p90 range. Example: "AWS Ashburn Campus · Large · 1,200 MW · committed 792 MW (range 480 – 1,080 MW)".

8. **"Methodology" link** (footer of panel) — opens info drawer with AllocationPct formula and data source attribution.

---

**Replay banner** (when a replay is active): slim strip below header: "Replay mode · Forecast issued 4 Feb 2021, 10 days before peak." + "Return to live" close button.

---

**Theme tokens:** Background #FFFFFF / panel #F7F8FA. Text #0B0F19 / #6B7280 / #9CA3AF. Brand #0F3D56. Stress: green #16A34A, amber #F59E0B, red #DC2626 (15% tint for chips, full saturation for dots). Fan bands: monochromatic teal at varying opacity. Typography: Inter or Geist, no serifs. Spacing: airy, Linear/sf.atmo.ai density.

**Do NOT design:** mobile layouts, dark mode, login/signup, fuel mix donut, weather raster, refresh button, any widgets beyond the seven listed above.

**Data realism:** live-node p50 demand ranges roughly Dominion 12–18 GW, CAISO SP15 15–25 GW, CAISO NP15 10–15 GW, ERCOT Houston 10–17 GW; allocation 60–80% green / 20–40% red. Do not invent fields.

---

## Verification

### Local dev (no COS, no teammate)

1. `pnpm install && pnpm dev` → Next.js on :3000.
2. `/` → map renders, 4 markers, colour-coded.
3. Click each marker → side panel, URL `?node=...`, all 7 widgets with data.
4. Fan chart: 7-day past demand line meets forecast bands at t=0.
5. Stress timeline: 240 cells.
6. Ensemble spread: 16 distinct lines.
7. DC cards: committed-draw bar with p10–p90 range.
8. Replay → "Texas 2021" → ERCOT Houston, banner, `actuals_overlay` line in upper quantiles.
9. Replay → "PJM 2023" → Dominion Hub.
10. Resize <1024px → desktop-only notice.

### Type & lint

- `pnpm tsc --noEmit` passes.
- `pnpm lint` passes.
- All `getX()` functions pass data through Zod without error on valid fixtures.
- Unknown node id → 404. Unknown replay id → 404.

### Production parity

- `GRIDCAST_DATA_SOURCE=cos`, `COS_BASE_URL` set → loads from COS, same components.
- Break COS URL → 502 + UI error state. No silent fixture serving.
- `GRIDCAST_DATA_SOURCE=cos`, `COS_BASE_URL` unset → app fails to start.
- `GRIDCAST_ENABLE_FIXTURE_FALLBACK=true` + COS broken → fixtures + "Showing cached demo data" banner.
- Lighthouse desktop ≥ 90 on `/` and `/?node=dominion-hub`.

---

## Teammate Reconciliation

The teammate's `backend/fixtures/generate.py` (commit `7c4b158`) must be
updated to conform to this spec. Full diff in `PLAN.md`. Key items:

| # | Change required |
|---|---|
| 1 | IDs: snake_case → kebab-case (`dominion-hub`, etc.) |
| 2 | Forecast target: `stress` → `demand_mw` (MW); stress is derived UI-side from quantiles vs threshold |
| 3 | Forecast shape: `points[{stress:{p10…}}]` → parallel arrays |
| 4 | History: move from `/live.last_7_days` to `/forecast.history` |
| 5 | `/live` payload: remove fuel_mix + history; add weather block |
| 6 | Remove `POST /refresh` and `refresh_response.json` |
| 7 | Replay: drop PNW 2022; rename remaining to kebab-case |
| 8 | Remove `stress_level` strings from all fixtures (UI derives) |
| 9 | Allocation: `{pct, pct_p50, pct_p10, p90_stress_fraction}` |
| 10 | Add `ensemble_spread` (16 GFS members × 240h) to each forecast |
| 11 | Add `data_centers` (3 per node, pre-computed `committed_draw_mw`) |
| 12 | Add `schema_version: 1` and `published_at` to all payloads |
| 13 | COS publication: versioned prefix + `active.json` manifest pointer |
| 14 | Fixture layout: `fixtures/{forecast,live,replay}/{id}.json` |

---

## Out of Scope

- Tier 2 operator dashboard
- Mobile layouts
- Dark mode
- `POST /refresh` / live inference
- Fuel mix donut, weather raster overlay
- Authentication, user accounts, waitlist
- Database
- Pacific Northwest 2022 replay event
