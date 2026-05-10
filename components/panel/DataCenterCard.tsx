import type { DataCenter } from '@/lib/types';

const TIER_LABEL: Record<DataCenter['tier'], string> = {
  large: 'Large',
  medium: 'Medium',
  small: 'Small',
};

export function DataCenterCard({ dc }: { dc: DataCenter }) {
  const initial = dc.operator.charAt(0).toUpperCase();
  const pctP50 = Math.round((dc.committed_draw_mw.p50 / dc.capacity_mw) * 100);
  const pctP10 = Math.round((dc.committed_draw_mw.p10 / dc.capacity_mw) * 100);
  const pctP90 = Math.round((dc.committed_draw_mw.p90 / dc.capacity_mw) * 100);

  return (
    <div className="border border-black/5 rounded-md px-3 py-2.5 bg-white">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded bg-brand/10 text-brand text-[13px] font-semibold flex items-center justify-center shrink-0">
          {initial}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-medium text-text-primary truncate">{dc.name}</div>
          <div className="text-[11px] text-text-tertiary">
            {TIER_LABEL[dc.tier]} · {dc.capacity_mw.toLocaleString()} MW
          </div>
        </div>
      </div>
      <div className="mt-2.5">
        <div className="relative h-1.5 rounded-full bg-black/[0.04]">
          <div
            className="absolute inset-y-0 bg-brand/15 rounded-full"
            style={{ left: `${pctP90}%`, width: `${Math.max(0, pctP10 - pctP90)}%` }}
          />
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-1 h-2.5 rounded-full bg-brand"
            style={{ left: `${pctP50}%` }}
          />
        </div>
        <div className="mt-1.5 text-[11px] text-text-secondary">
          Committed {dc.committed_draw_mw.p50.toLocaleString()} MW
          <span className="text-text-tertiary"> · range {dc.committed_draw_mw.p90.toLocaleString()}–{dc.committed_draw_mw.p10.toLocaleString()} MW</span>
        </div>
      </div>
    </div>
  );
}
