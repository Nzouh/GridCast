import type { Node, ForecastResponse, ReplayResponse } from '@/lib/types';
import { NodePanelHeader } from './NodePanelHeader';
import { DataCenterList } from './DataCenterList';
import { StaleBanner } from '../shell/StaleBanner';
import { AllocationGauge } from './AllocationGauge';
import { FanChart } from './FanChart';
import { StressTimeline } from './StressTimeline';
import { EnsembleSpread } from './EnsembleSpread';

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
  const payload = replay ?? forecast;
  const issuedAt = payload?.issued_at ?? null;

  return (
    <aside
      className="absolute top-0 right-0 h-full w-[420px] bg-white border-l border-black/5 shadow-[0_0_40px_rgba(11,15,25,0.04)] overflow-y-auto z-20"
      style={{ animation: 'gc-slide-in 240ms ease-out' }}
    >
      {stale && publishedAt ? <StaleBanner publishedAt={publishedAt} /> : null}
      <NodePanelHeader node={node} issuedAt={issuedAt} closeHref={closeHref} />
      <div className="px-6 py-5 flex flex-col gap-6">
        {payload ? (
          <>
            <AllocationGauge allocation={payload.allocation} />
            <FanChart payload={payload} />
            <StressTimeline points={payload.stress_timeline} />
            <EnsembleSpread spread={payload.ensemble_spread} />
            <DataCenterList items={payload.data_centers} />
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
