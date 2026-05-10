'use client';

import type { EnsembleSpread as EnsembleSpreadType } from '@/lib/types';

const T = {
  text: '#0B0F19',
  tertiary: '#9CA3AF',
  gridLine: '#EEF1F5',
  fanBand: '#0F3D56',
  fontMono: 'var(--font-jbmono), "JetBrains Mono", ui-monospace, monospace',
};

export function EnsembleSpread({ ensemble }: { ensemble: EnsembleSpreadType }) {
  const W = 372, H = 130, padL = 32, padR = 8, padT = 14, padB = 22;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const N = ensemble.members[0].length;

  const allVals = ensemble.members.flat();
  const ymin = Math.floor(Math.min(...allVals)) - 1;
  const ymax = Math.ceil(Math.max(...allVals)) + 1;

  const x = (i: number) => padL + (i / (N - 1)) * innerW;
  const y = (v: number) => padT + innerH - ((v - ymin) / (ymax - ymin)) * innerH;

  const mean = ensemble.members[0].map((_, i) =>
    ensemble.members.reduce((a, m) => a + m[i], 0) / ensemble.members.length
  );
  const meanPath = mean.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');

  return (
    <div style={{ padding: '8px 16px 4px' }}>
      <div style={{
        color: T.tertiary, fontSize: 11, letterSpacing: '0.05em',
        textTransform: 'uppercase', fontWeight: 500, padding: '0 0 4px',
        display: 'flex', justifyContent: 'space-between', fontFamily: T.fontMono,
      }}>
        <span>Weather ensemble</span>
        <span style={{ textTransform: 'none', letterSpacing: 0 }}>
          {ensemble.members.length} GFS members · °C
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}>
        {[ymin, Math.round((ymin + ymax) / 2), ymax].map((v, i) => (
          <g key={i}>
            <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} stroke={T.gridLine} />
            <text x={padL - 5} y={y(v) + 3} textAnchor="end"
                  fontSize="9" fontFamily={T.fontMono} fill={T.tertiary}>{v}°</text>
          </g>
        ))}
        {ensemble.members.map((m, mi) => (
          <path key={mi}
                d={m.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')}
                stroke={T.fanBand} strokeWidth="0.6" fill="none" opacity="0.32" />
        ))}
        <path d={meanPath} stroke={T.text} strokeWidth="1.4" fill="none" opacity="0.9" />
        {[2, 5, 8].map((d) => (
          <text key={d} x={x(d * 24)} y={H - 6} textAnchor="middle"
                fontSize="9" fontFamily={T.fontMono} fill={T.tertiary}>D+{d}</text>
        ))}
      </svg>
    </div>
  );
}
