import type { EnsembleSpread as EnsembleSpreadType } from '@/lib/types';
import { linePath, minMax, scaleLinear } from './chartUtils';

export function EnsembleSpread({ spread }: { spread: EnsembleSpreadType }) {
  const width = 372;
  const height = 132;
  const pad = { top: 12, right: 10, bottom: 18, left: 32 };
  const values = spread.members.flat();
  const [rawMin, rawMax] = minMax(values);
  const yDomain: [number, number] = [rawMin - 1, rawMax + 1];
  const xFor = (i: number) => pad.left + scaleLinear(i, [0, spread.timestamps.length - 1], [0, width - pad.left - pad.right]);
  const yFor = (v: number) => pad.top + scaleLinear(v, yDomain, [height - pad.top - pad.bottom, 0]);
  const mean = spread.timestamps.map((_, i) => spread.members.reduce((sum, member) => sum + member[i], 0) / spread.members.length);

  return (
    <section>
      <div className="flex items-end justify-between mb-2">
        <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Weather ensemble</div>
        <div className="text-[11px] text-text-tertiary">{spread.members.length} GFS members</div>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto rounded-md bg-surface-panel border border-black/5">
        {spread.members.map((member, idx) => (
          <path
            key={idx}
            d={linePath(member.map((value, i) => [xFor(i), yFor(value)] as [number, number]))}
            fill="none"
            stroke="#0F3D56"
            strokeOpacity="0.18"
            strokeWidth="1"
          />
        ))}
        <path d={linePath(mean.map((value, i) => [xFor(i), yFor(value)] as [number, number]))} fill="none" stroke="#0F3D56" strokeWidth="2" />
        <text x="7" y={pad.top + 8} fontSize="10" fill="#9CA3AF">{Math.round(yDomain[1])}C</text>
        <text x="7" y={height - pad.bottom} fontSize="10" fill="#9CA3AF">{Math.round(yDomain[0])}C</text>
      </svg>
    </section>
  );
}
