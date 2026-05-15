import type { EnsembleSpread as EnsembleSpreadType } from '@/lib/types';
import { minMax, scaleLinear, smoothLine } from './chartUtils';

export function EnsembleSpread({ spread }: { spread: EnsembleSpreadType }) {
  const width = 372;
  const height = 130;
  const pad = { top: 12, right: 10, bottom: 18, left: 32 };
  const values = spread.members.flat();
  const [rawMin, rawMax] = minMax(values);
  const yDomain: [number, number] = [Math.floor(rawMin) - 1, Math.ceil(rawMax) + 1];
  const xFor = (i: number) => pad.left + scaleLinear(i, [0, spread.timestamps.length - 1], [0, width - pad.left - pad.right]);
  const yFor = (v: number) => pad.top + scaleLinear(v, yDomain, [height - pad.top - pad.bottom, 0]);
  const mean = spread.timestamps.map((_, i) => spread.members.reduce((sum, member) => sum + member[i], 0) / spread.members.length);
  const yTicks = [yDomain[0], Math.round((yDomain[0] + yDomain[1]) / 2), yDomain[1]];

  return (
    <section data-gc-tutorial="ensemble">
      <div className="gc-section-head">
        <span>Weather ensemble</span>
        <span>{spread.members.length} GFS members</span>
      </div>
      <div className="rounded-lg bg-surface-panel border border-border">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto block">
          {yTicks.map((value) => (
            <g key={value}>
              <line x1={pad.left} x2={width - pad.right} y1={yFor(value)} y2={yFor(value)} stroke="#ECEEF2" />
              <text
                x={pad.left - 5}
                y={yFor(value) + 3}
                textAnchor="end"
                fontSize="9.5"
                fontFamily="var(--font-jbmono), JetBrains Mono, ui-monospace, monospace"
                fill="#9CA3AF"
              >
                {value}&deg;
              </text>
            </g>
          ))}
          {spread.members.map((member, idx) => (
            <path
              key={idx}
              d={smoothLine(member.map((value, i) => [xFor(i), yFor(value)] as [number, number]))}
              fill="none"
              stroke="#0F3D56"
              strokeOpacity="0.16"
              strokeWidth="0.9"
            />
          ))}
          <path
            d={smoothLine(mean.map((value, i) => [xFor(i), yFor(value)] as [number, number]))}
            fill="none"
            stroke="#0F3D56"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {[2, 5, 8].map((day) => (
            <text
              key={day}
              x={xFor(day * 24)}
              y={height - 5}
              textAnchor="middle"
              fontSize="9.5"
              fontFamily="var(--font-jbmono), JetBrains Mono, ui-monospace, monospace"
              fill="#9CA3AF"
            >
              D+{day}
            </text>
          ))}
        </svg>
      </div>
    </section>
  );
}
