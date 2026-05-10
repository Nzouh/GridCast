'use client';

import { useState, useRef } from 'react';
import type { QuantileSeries, HistorySeries } from '@/lib/types';

const T = {
  text: '#0B0F19',
  secondary: '#6B7280',
  tertiary: '#9CA3AF',
  gridLine: '#EEF1F5',
  fanBand: '#0F3D56',
  amber: '#F59E0B',
  red: '#DC2626',
  fontMono: 'var(--font-jbmono), "JetBrains Mono", ui-monospace, monospace',
};

function fmtMW(v: number): string {
  if (v >= 1000) return `${(v / 1000).toFixed(0)}k`;
  return String(Math.round(v));
}

type Props = {
  forecast: QuantileSeries;
  history: HistorySeries;
  threshold: number;
  actualsOverlay?: number[] | null;
};

export function FanChart({ forecast, history, threshold, actualsOverlay }: Props) {
  const W = 372, H = 200, padL = 40, padR = 8, padT = 14, padB = 22;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const NH = history.demand_mw.length;
  const NF = forecast.p50.length;
  const totalPts = NH + NF;

  const allVals = [
    ...history.demand_mw, ...forecast.p10, ...forecast.p90,
    ...(actualsOverlay ?? []),
  ];
  const ymax = Math.max(threshold * 1.4, ...allVals) * 1.05;
  const ymin = 0;

  const x = (i: number) => padL + (i / (totalPts - 1)) * innerW;
  const y = (v: number) => padT + innerH - ((v - ymin) / (ymax - ymin)) * innerH;

  const histPath = history.demand_mw
    .map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');

  function bandPath(low: number[], high: number[]) {
    const fwd = low.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(NH + i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    const back = high.map((_v, i) =>
      `L${x(NH + high.length - 1 - i).toFixed(1)},${y(high[high.length - 1 - i]).toFixed(1)}`
    ).join(' ');
    return fwd + ' ' + back + ' Z';
  }

  const p50Path = forecast.p50
    .map((v, i) => `${i === 0 ? 'M' : 'L'}${x(NH + i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');

  const actualsPath = actualsOverlay
    ? actualsOverlay.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(NH + i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
    : null;

  const yTicks = [0, ymax * 0.25, ymax * 0.5, ymax * 0.75].map(Math.round);
  const xTicks: { d: number; i: number }[] = [];
  for (let d = -7; d <= 10; d += 2) {
    const idx = NH - 1 + d * 24;
    if (idx >= 0 && idx < totalPts) xTicks.push({ d, i: idx });
  }

  const [hover, setHover] = useState<number | null>(null);
  const ref = useRef<SVGSVGElement>(null);

  function onMove(e: React.MouseEvent) {
    const r = ref.current?.getBoundingClientRect();
    if (!r) return;
    const px = ((e.clientX - r.left) / r.width) * W;
    if (px < padL || px > padL + innerW) { setHover(null); return; }
    const i = Math.round(((px - padL) / innerW) * (totalPts - 1));
    setHover(i);
  }

  return (
    <div style={{ padding: '8px 16px 4px' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
        padding: '0 8px 6px', color: T.tertiary, fontSize: 11, letterSpacing: '0.05em',
        textTransform: 'uppercase', fontWeight: 500, fontFamily: T.fontMono,
      }}>
        <span>Demand · MW</span>
        <span style={{ textTransform: 'none', letterSpacing: 0 }}>7d history · 10d forecast</span>
      </div>
      <svg ref={ref} viewBox={`0 0 ${W} ${H}`} onMouseMove={onMove} onMouseLeave={() => setHover(null)}
           style={{ width: '100%', display: 'block', cursor: 'crosshair' }}>
        {yTicks.map((v, i) => (
          <g key={i}>
            <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} stroke={T.gridLine} strokeWidth="1" />
            <text x={padL - 6} y={y(v) + 3} textAnchor="end" fontSize="9.5"
                  fontFamily={T.fontMono} fill={T.tertiary}>{fmtMW(v)}</text>
          </g>
        ))}
        <line x1={padL} x2={W - padR} y1={y(threshold)} y2={y(threshold)}
              stroke={T.amber} strokeWidth="1" strokeDasharray="3 3" />
        <text x={W - padR - 4} y={y(threshold) - 3} textAnchor="end"
              fontSize="9" fontFamily={T.fontMono} fill={T.amber}>stress threshold</text>
        <line x1={x(NH - 0.5)} x2={x(NH - 0.5)} y1={padT} y2={padT + innerH}
              stroke={T.gridLine} strokeWidth="1" strokeDasharray="2 2" />
        <text x={x(NH - 0.5)} y={padT - 3} textAnchor="middle"
              fontSize="9" fontFamily={T.fontMono} fill={T.tertiary}>NOW</text>
        <path d={bandPath(forecast.p10, forecast.p90)} fill={T.fanBand} opacity="0.18" />
        <path d={bandPath(forecast.p25, forecast.p75)} fill={T.fanBand} opacity="0.32" />
        <path d={p50Path} stroke={T.fanBand} strokeWidth="1.5" fill="none" />
        <path d={histPath} stroke={T.text} strokeWidth="1.25" fill="none" opacity="0.85" />
        {actualsPath && (
          <path d={actualsPath} stroke={T.red} strokeWidth="1.6" fill="none" strokeLinecap="round" />
        )}
        {xTicks.map(({ d, i }) => (
          <text key={i} x={x(i)} y={H - 6} textAnchor="middle"
                fontSize="9.5" fontFamily={T.fontMono} fill={T.tertiary}>
            {d === 0 ? '0' : d > 0 ? `+${d}d` : `${d}d`}
          </text>
        ))}
        {hover != null && (() => {
          const inForecast = hover >= NH;
          const v = inForecast ? forecast.p50[hover - NH] : history.demand_mw[hover];
          const tipX = Math.min(x(hover) + 8, W - 92);
          return (
            <g>
              <line x1={x(hover)} x2={x(hover)} y1={padT} y2={padT + innerH}
                    stroke={T.text} strokeWidth="1" opacity="0.4" />
              <circle cx={x(hover)} cy={y(v)} r="3" fill={T.text} />
              <g transform={`translate(${tipX}, ${padT + 4})`}>
                <rect x="0" y="0" width="88" height="30" rx="3" fill={T.text} opacity="0.92" />
                <text x="6" y="13" fontSize="9.5" fontFamily={T.fontMono} fill="#fff">
                  {inForecast ? `+${hover - NH}h` : `${hover - NH}h`}
                </text>
                <text x="6" y="24" fontSize="10.5" fontFamily={T.fontMono} fill="#fff" fontWeight="600">
                  {fmtMW(v)} MW
                </text>
              </g>
            </g>
          );
        })()}
      </svg>
    </div>
  );
}
