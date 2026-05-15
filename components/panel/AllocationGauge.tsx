import type { Allocation, StressLevel } from '@/lib/types';

const ACCENT: Record<StressLevel, string> = {
  green: '#0F3D56',
  amber: 'oklch(0.78 0.16 78)',
  red: 'oklch(0.62 0.21 27)',
};

export function AllocationGauge({
  allocation,
  level,
}: {
  allocation: Allocation;
  level: StressLevel;
}) {
  const accent = ACCENT[level];

  return (
    <section data-gc-tutorial="allocation">
      <div className="gc-label">
        Recommended allocation
      </div>
      <div className="mt-1 flex items-end gap-3.5">
        <div className="text-[78px] leading-[0.95] font-semibold tracking-[-0.035em] text-text-primary tabular-nums">
          {allocation.pct}
          <span className="text-[44px] font-medium text-text-secondary">%</span>
        </div>
        <div className="pb-2.5 font-mono text-[11.5px] leading-[1.55] text-text-secondary tabular-nums">
          p50&nbsp;&nbsp;{allocation.pct_p50}%<br />
          p10&nbsp;&nbsp;{allocation.pct_p10}%
        </div>
      </div>
      <div className="mt-3 h-1 rounded-full bg-[#0B0F1910] relative overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 rounded-full"
          style={{ width: `${allocation.pct}%`, background: accent }}
        />
        <div
          className="absolute inset-y-0 rounded-full"
          style={{
            left: `${allocation.pct}%`,
            width: `${Math.max(0, allocation.pct_p10 - allocation.pct)}%`,
            background: accent,
            opacity: 0.22,
          }}
        />
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[10.5px] text-text-tertiary tabular-nums">
        <span>
          Stress fraction p90 <span aria-hidden="true">&middot;</span>{' '}
          {Math.round(allocation.p90_stress_fraction * 100)}%
        </span>
        <span>0&ndash;100%</span>
      </div>
    </section>
  );
}
