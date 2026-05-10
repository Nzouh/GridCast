'use client';

import { useState } from 'react';
import type { StressTimelinePoint } from '@/lib/types';

const T = {
  text: '#0B0F19',
  secondary: '#6B7280',
  tertiary: '#9CA3AF',
  green: '#16A34A',
  amber: '#F59E0B',
  red: '#DC2626',
  fontMono: 'var(--font-jbmono), "JetBrains Mono", ui-monospace, monospace',
};

function stressColor(p: number) {
  if (p < 0.2) return T.green;
  if (p < 0.5) return T.amber;
  return T.red;
}

export function StressStrip({ stress }: { stress: StressTimelinePoint[] }) {
  const W = 372, H = 32, stripH = 14;
  const N = stress.length;
  const cellW = W / N;
  const [hover, setHover] = useState<number | null>(null);

  return (
    <div style={{ padding: '10px 16px 6px' }}>
      <div style={{
        color: T.tertiary, fontSize: 11, letterSpacing: '0.05em',
        textTransform: 'uppercase', fontWeight: 500, padding: '0 0 6px',
        fontFamily: T.fontMono,
      }}>
        Stress probability · 240 hours
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}
           onMouseMove={(e) => {
             const r = e.currentTarget.getBoundingClientRect();
             const px = ((e.clientX - r.left) / r.width) * W;
             setHover(Math.max(0, Math.min(N - 1, Math.floor(px / cellW))));
           }}
           onMouseLeave={() => setHover(null)}>
        {stress.map((s, i) => (
          <rect key={i} x={i * cellW} y={H - stripH} width={cellW + 0.4} height={stripH}
                fill={stressColor(s.stress_probability)} opacity={hover === i ? 1 : 0.85} />
        ))}
        {[1, 3, 5, 7, 9].map((d) => (
          <g key={d}>
            <line x1={d * 24 * cellW} x2={d * 24 * cellW}
                  y1={H - stripH - 3} y2={H - stripH}
                  stroke={T.tertiary} strokeWidth="1" />
            <text x={d * 24 * cellW} y={H - stripH - 6}
                  fontSize="9" fontFamily={T.fontMono} fill={T.tertiary} textAnchor="middle">
              D+{d}
            </text>
          </g>
        ))}
        {hover != null && (
          <line x1={(hover + 0.5) * cellW} x2={(hover + 0.5) * cellW}
                y1={0} y2={H} stroke={T.text} opacity="0.6" strokeWidth="1" />
        )}
      </svg>
      <div style={{
        fontSize: 10.5, fontFamily: T.fontMono, color: T.secondary,
        height: 14, marginTop: 2,
      }}>
        {hover != null
          ? `+${hover}h · ${(stress[hover].stress_probability * 100).toFixed(0)}% probability`
          : <span style={{ color: T.tertiary }}>hover for hourly probability</span>
        }
      </div>
    </div>
  );
}
