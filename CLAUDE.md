# GridCast — Web App

## What this repo is

GridCast is a hackathon demo + startup-base that forecasts US electricity
grid stress for 4 transmission nodes over a 10-day horizon and outputs a
recommended power-allocation % for co-located AI data-centre tenants.

This repo is **the web app** — frontend + backend — in **TypeScript + Next.js**.
ML model, training, and inference live in a separate teammate workstream.
Integration happens through a stable JSON API contract (see `SPEC.md`).

## Source of truth

- `gridcast_design.tex` — original design doc: nodes, headline formula,
  product tiers. Read before making product decisions.
- `SPEC.md` — authoritative web-app spec: API contract, component tree,
  mock/live strategy, data-centre rosters, Claude-design prompt.
- `PLAN.md` — full brainstorm + claudex adversarial review history.
  Read for *why* decisions were made.
- `TEAM_SPLIT.md` — original team boundary (superseded: this repo now
  owns both FE and BE, not just FE).

## Stack

| Layer | Choice |
|---|---|
| Framework | Next.js (App Router) + TypeScript |
| Styling | Tailwind CSS |
| Map | Mapbox GL JS via `react-map-gl` (`NEXT_PUBLIC_MAPBOX_TOKEN`) |
| Charts | Visx (D3-based) |
| Hosting | Vercel |
| Data | IBM COS (prod) / `fixtures/` (dev) |
| DB / Auth | None |

## API contract — 4 endpoints (frozen)

```
GET  /api/nodes
GET  /api/nodes/[id]/forecast
GET  /api/nodes/[id]/live
GET  /api/replay/[event_id]
```

`POST /api/nodes/[id]/refresh` does NOT exist. Shapes are in `SPEC.md`.
Teammate's COS objects must conform exactly. Do not change shapes without
coordinating with the teammate.

## Working agreements

- Never mock at component level. All data flows through `lib/dataSource.ts`.
- `GRIDCAST_DATA_SOURCE=fixtures` (dev) / `cos` (prod). One env var swap.
- COS failure in prod mode → 502 error state, never silent fixture serving.
- All IDs validated against hardcoded allowlists before any path construction.
- Props crossing RSC→client boundary must be plain JSON (ISO strings, no
  Date objects). `MapShell` wraps Mapbox with `dynamic({ ssr: false })`.
- Zod validates all COS/fixture reads at the data-source boundary.
- Replay events: `texas-2021` (ERCOT Houston) + `pjm-2023` (Dominion Hub).
  PNW 2022 dropped — no matching node.

## Key files

```
lib/dataSource.ts   server-only; fixture/COS switch + Zod validation
lib/types.ts        shared TypeScript types for all API shapes
lib/formulas.ts     stress level from probability; AllocationPct formula
fixtures/           local JSON fixtures (dev mode)
SPEC.md             full spec — read this before implementing anything
```
