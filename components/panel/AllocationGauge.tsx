import type { Allocation } from '@/lib/types';

export function AllocationGauge({ allocation }: { allocation: Allocation }) {
  return (
    <section>
      <div className="text-[10px] uppercase tracking-wider text-text-tertiary mb-1">
        Recommended allocation
      </div>
      <div className="flex items-end gap-3">
        <div className="text-[76px] leading-none font-semibold tracking-tight text-text-primary">
          {allocation.pct}%
        </div>
        <div className="pb-2 text-[12px] text-text-secondary">
          p50 {allocation.pct_p50}%<br />
          p10 {allocation.pct_p10}%
        </div>
      </div>
      <div className="mt-3 h-2 rounded-full bg-black/[0.05] relative overflow-hidden">
        <div className="absolute inset-y-0 left-0 bg-brand" style={{ width: `${allocation.pct}%` }} />
        <div className="absolute inset-y-0 bg-brand/25" style={{ left: `${allocation.pct}%`, width: `${Math.max(0, allocation.pct_p10 - allocation.pct)}%` }} />
      </div>
      <div className="mt-1.5 text-[11px] text-text-tertiary">
        Stress fraction p90: {Math.round(allocation.p90_stress_fraction * 100)}%
      </div>
    </section>
  );
}
