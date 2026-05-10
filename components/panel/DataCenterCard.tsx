import type { DataCenter } from '@/lib/types';

export function DataCenterCard({ dc }: { dc: DataCenter }) {
  const initial = dc.operator.charAt(0).toUpperCase();
  const pctP50 = Math.round((dc.committed_draw_mw.p50 / dc.capacity_mw) * 100);
  const pctP10 = Math.round((dc.committed_draw_mw.p10 / dc.capacity_mw) * 100);
  const pctP90 = Math.round((dc.committed_draw_mw.p90 / dc.capacity_mw) * 100);

  return (
    <div className="border border-border rounded-lg px-3 py-2.5 bg-white">
      <div className="flex items-center gap-2.5">
        <div className="w-[30px] h-[30px] rounded-md bg-brand/[0.08] text-brand text-[13px] font-semibold flex items-center justify-center shrink-0">
          {initial}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-medium text-text-primary truncate">{dc.name}</div>
          <div className="font-mono text-[11px] text-text-tertiary">
            {dc.operator} <span aria-hidden="true">&middot;</span> {dc.capacity_mw.toLocaleString()} MW
          </div>
        </div>
      </div>
      <div className="mt-2.5">
        <div className="relative h-1 rounded-full bg-[#0B0F1908]">
          <div
            className="absolute inset-y-0 rounded-full bg-[rgba(15,61,86,0.18)]"
            style={{ left: `${pctP90}%`, width: `${Math.max(0, pctP10 - pctP90)}%` }}
          />
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-0.5 h-2.5 rounded-sm bg-brand"
            style={{ left: `${pctP50}%` }}
          />
        </div>
        <div className="mt-1.5 flex justify-between gap-3 font-mono text-[11px] text-text-secondary tabular-nums">
          <span>p50&nbsp;{dc.committed_draw_mw.p50.toLocaleString()} MW</span>
          <span className="text-text-tertiary">
            {dc.committed_draw_mw.p90.toLocaleString()}&ndash;{dc.committed_draw_mw.p10.toLocaleString()} MW
          </span>
        </div>
      </div>
    </div>
  );
}
