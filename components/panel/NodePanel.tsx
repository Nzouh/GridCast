import type { Node, ForecastResponse, ReplayResponse } from '@/lib/types';
import { NodePanelHeader } from './NodePanelHeader';
import { DataCenterList } from './DataCenterList';
import { StaleBanner } from '../shell/StaleBanner';

export function NodePanel({
  node,
  forecast,
  replay,
  closeHref,
  stale,
  publishedAt,
}: {
  node: Node;
  forecast: ForecastResponse | null;
  replay: ReplayResponse | null;
  closeHref: string;
  stale: boolean;
  publishedAt: string | null;
}) {
  const issuedAt = replay?.issued_at ?? forecast?.issued_at ?? null;
  const dataCenters = replay?.data_centers ?? forecast?.data_centers ?? [];
  const loaded = forecast !== null || replay !== null;

  return (
    <aside
      className="absolute top-0 right-0 h-full w-[420px] bg-white border-l border-black/5 shadow-[0_0_40px_rgba(11,15,25,0.04)] overflow-y-auto z-20"
      style={{ animation: 'gc-slide-in 240ms ease-out' }}
    >
      {stale && publishedAt ? <StaleBanner publishedAt={publishedAt} /> : null}
      <NodePanelHeader node={node} issuedAt={issuedAt} closeHref={closeHref} />
      <div className="px-6 py-5 flex flex-col gap-6">
        {loaded ? (
          <>
            <ChartsPlaceholder />
            <DataCenterList items={dataCenters} />
          </>
        ) : (
          <div className="rounded border border-stress-amber/30 bg-stress-amber/[0.06] p-3 text-[12px] text-text-primary">
            Forecast data unavailable for this node. Try again later.
          </div>
        )}
      </div>
      <div className="px-6 pb-6 pt-2 text-[11px] text-text-tertiary border-t border-black/5">
        Methodology
      </div>
    </aside>
  );
}

function ChartsPlaceholder() {
  const widgets = ['AllocationGauge', 'FanChart', 'StressTimeline', 'EnsembleSpread'];
  return (
    <div className="rounded-md border border-dashed border-black/10 bg-surface-panel p-4">
      <div className="text-[11px] uppercase tracking-wider text-text-tertiary mb-2">
        Charts — Pass B
      </div>
      <div className="flex flex-wrap gap-1.5">
        {widgets.map((w) => (
          <span
            key={w}
            className="text-[11px] px-2 py-0.5 rounded bg-white border border-black/10 text-text-secondary"
          >
            {w}
          </span>
        ))}
      </div>
    </div>
  );
}
