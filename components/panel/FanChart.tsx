import type { ForecastResponse, ReplayResponse } from '@/lib/types';
import { areaPath, formatMw, linePath, minMax, scaleLinear } from './chartUtils';

type Payload = ForecastResponse | ReplayResponse;

export function FanChart({ payload }: { payload: Payload }) {
  const width = 372;
  const height = 250;
  const pad = { top: 16, right: 12, bottom: 26, left: 42 };
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
  const padding = (rawMax - rawMin) * 0.08;
  const yDomain: [number, number] = [rawMin - padding, rawMax + padding];
  const xFor = (i: number) => pad.left + scaleLinear(i, [0, total - 1], [0, innerW]);
  const yFor = (v: number) => pad.top + scaleLinear(v, yDomain, [innerH, 0]);

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

  return (
    <section>
      <div className="flex items-end justify-between mb-2">
        <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Demand forecast</div>
        <div className="text-[11px] text-text-tertiary">7d history + 10d TFT</div>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto rounded-md bg-surface-panel border border-black/5">
        <line x1={pad.left} x2={width - pad.right} y1={thresholdY} y2={thresholdY} stroke="#DC2626" strokeDasharray="4 4" strokeWidth="1" />
        <text x={pad.left + 4} y={Math.max(12, thresholdY - 5)} fontSize="10" fill="#DC2626">threshold</text>
        <path d={areaPath(p90, p10)} fill="rgb(15 61 86 / 0.12)" />
        <path d={areaPath(p75, p25)} fill="rgb(15 61 86 / 0.28)" />
        <path d={linePath(historyLine)} fill="none" stroke="#6B7280" strokeWidth="1.8" />
        <path d={linePath(p50)} fill="none" stroke="#0F3D56" strokeWidth="2.3" />
        {actualLine.length > 0 ? <path d={linePath(actualLine)} fill="none" stroke="#DC2626" strokeWidth="2" /> : null}
        <line x1={nowX} x2={nowX} y1={pad.top} y2={height - pad.bottom} stroke="#0B0F19" strokeOpacity="0.18" />
        <text x={nowX + 4} y={height - 10} fontSize="10" fill="#9CA3AF">now</text>
        <text x="8" y={pad.top + 8} fontSize="10" fill="#9CA3AF">{formatMw(yDomain[1])}</text>
        <text x="8" y={height - pad.bottom} fontSize="10" fill="#9CA3AF">{formatMw(yDomain[0])}</text>
      </svg>
    </section>
  );
}
