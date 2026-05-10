import type { ForecastResponse, ReplayResponse } from '@/lib/types';
import { formatMw, minMax, scaleLinear, smoothBand, smoothLine } from './chartUtils';

type Payload = ForecastResponse | ReplayResponse;

export function FanChart({ payload }: { payload: Payload }) {
  const width = 372;
  const height = 210;
  const pad = { top: 18, right: 12, bottom: 22, left: 44 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const history = payload.history.demand_mw;
  const forecast = payload.forecast;
  const total = history.length + forecast.timestamps.length;
  const allValues = [
    ...history,
    ...forecast.p10,
    ...forecast.p25,
    ...forecast.p50,
    ...forecast.p75,
    ...forecast.p90,
    payload.stress_threshold_demand_mw,
    ...('actuals_overlay' in payload ? payload.actuals_overlay.demand_mw : []),
  ];
  const [rawMin, rawMax] = minMax(allValues);
  const padding = (rawMax - rawMin) * 0.12;
  const yDomain: [number, number] = [rawMin - padding, rawMax + padding];
  const xFor = (i: number) => pad.left + scaleLinear(i, [0, total - 1], [0, innerW]);
  const yFor = (v: number) => pad.top + scaleLinear(v, yDomain, [innerH, 0]);
  const gradientSuffix = `${payload.node_id}-${'event_id' in payload ? payload.event_id : 'live'}`.replace(/[^a-z0-9-]/gi, '-');
  const outerGradientId = `fanOuterGrad-${gradientSuffix}`;
  const innerGradientId = `fanInnerGrad-${gradientSuffix}`;

  const historyLine = history.map((value, i) => [xFor(i), yFor(value)] as [number, number]);
  const offset = history.length;
  const p10 = forecast.p10.map((value, i) => [xFor(offset + i), yFor(value)] as [number, number]);
  const p25 = forecast.p25.map((value, i) => [xFor(offset + i), yFor(value)] as [number, number]);
  const p50 = forecast.p50.map((value, i) => [xFor(offset + i), yFor(value)] as [number, number]);
  const p75 = forecast.p75.map((value, i) => [xFor(offset + i), yFor(value)] as [number, number]);
  const p90 = forecast.p90.map((value, i) => [xFor(offset + i), yFor(value)] as [number, number]);
  const thresholdY = yFor(payload.stress_threshold_demand_mw);
  const nowX = xFor(history.length - 1);
  const actualLine =
    'actuals_overlay' in payload
      ? payload.actuals_overlay.demand_mw.map((value, i) => [xFor(offset + i), yFor(value)] as [number, number])
      : [];
  const ticks = [
    { y: yFor(yDomain[1]), label: formatMw(yDomain[1]) },
    { y: yFor(yDomain[0]), label: formatMw(yDomain[0]) },
  ];

  return (
    <section>
      <div className="gc-section-head">
        <span>Demand forecast</span>
        <span>
          7d history <span aria-hidden="true">&middot;</span> 10d TFT
        </span>
      </div>
      <div className="rounded-lg bg-surface-panel border border-border">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto block">
          <defs>
            <linearGradient id={innerGradientId} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#0F3D56" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#0F3D56" stopOpacity="0.30" />
            </linearGradient>
            <linearGradient id={outerGradientId} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#0F3D56" stopOpacity="0.06" />
              <stop offset="100%" stopColor="#0F3D56" stopOpacity="0.14" />
            </linearGradient>
          </defs>

          {ticks.map((tick) => (
            <line
              key={tick.label}
              x1={pad.left}
              x2={width - pad.right}
              y1={tick.y}
              y2={tick.y}
              stroke="#ECEEF2"
              strokeWidth="1"
            />
          ))}

          <path d={smoothBand(p10, p90)} fill={`url(#${outerGradientId})`} />
          <path d={smoothBand(p25, p75)} fill={`url(#${innerGradientId})`} />
          <path
            d={smoothLine(historyLine)}
            fill="none"
            stroke="#3D4453"
            strokeWidth="1.6"
            strokeOpacity="0.85"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d={smoothLine(p50)}
            fill="none"
            stroke="#0F3D56"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {actualLine.length > 0 ? (
            <path
              d={smoothLine(actualLine)}
              fill="none"
              stroke="oklch(0.62 0.21 27)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ) : null}
          <line
            x1={pad.left}
            x2={width - pad.right}
            y1={thresholdY}
            y2={thresholdY}
            stroke="oklch(0.62 0.21 27)"
            strokeOpacity="0.55"
            strokeDasharray="3 4"
            strokeWidth="1"
          />
          <text
            x={pad.left + 6}
            y={Math.max(pad.top + 9, thresholdY - 5)}
            fontSize="9.5"
            fontFamily="var(--font-jbmono), JetBrains Mono, ui-monospace, monospace"
            fill="oklch(0.62 0.21 27)"
            fillOpacity="0.85"
          >
            threshold
          </text>
          <line
            x1={nowX}
            x2={nowX}
            y1={pad.top}
            y2={height - pad.bottom}
            stroke="#0B0F19"
            strokeOpacity="0.18"
            strokeWidth="1"
          />
          <text
            x={nowX}
            y={height - 6}
            fontSize="9.5"
            fontFamily="var(--font-jbmono), JetBrains Mono, ui-monospace, monospace"
            fill="#9CA3AF"
            textAnchor="middle"
          >
            now
          </text>
          {ticks.map((tick, index) => (
            <text
              key={`${tick.label}-${index}`}
              x={pad.left - 6}
              y={tick.y + (index === 0 ? 9 : 0)}
              textAnchor="end"
              fontSize="9.5"
              fontFamily="var(--font-jbmono), JetBrains Mono, ui-monospace, monospace"
              fill="#9CA3AF"
            >
              {tick.label}
            </text>
          ))}
        </svg>
      </div>
    </section>
  );
}
