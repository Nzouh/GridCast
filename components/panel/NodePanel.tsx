import type { Node, ForecastResponse, ReplayResponse } from '@/lib/types';
import { NodePanelHeader } from './NodePanelHeader';
import { DataCenterList } from './DataCenterList';
import { StaleBanner } from '../shell/StaleBanner';
import { AllocationGauge } from './AllocationGauge';
import { FanChart } from './FanChart';
import { StressTimeline } from './StressTimeline';
import { EnsembleSpread } from './EnsembleSpread';
import { stressLevel } from '@/lib/formulas';

const LEVEL_COLOR: Record<'green' | 'amber' | 'red', string> = {
  green: 'oklch(0.66 0.16 150)',
  amber: 'oklch(0.78 0.16 78)',
  red: 'oklch(0.62 0.21 27)',
};

const LEVEL_TINT: Record<'green' | 'amber' | 'red', string> = {
  green: 'rgba(22,163,74,0.045)',
  amber: 'rgba(245,158,11,0.045)',
  red: 'rgba(220,38,38,0.045)',
};

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
  const level = stressLevel(node.stress_probability);

  return (
    <aside
      key={`${node.id}-${replay?.event_id ?? 'live'}`}
      className="absolute top-0 right-0 h-full w-[420px] bg-white border-l border-border shadow-[0_0_40px_rgba(11,15,25,0.04)] overflow-y-auto overflow-x-hidden z-20"
      style={{ animation: 'gc-slide-in 280ms cubic-bezier(.2,.7,.3,1)' }}
    >
      <div
        className="absolute left-0 top-0 bottom-0 w-[3px] opacity-[0.85]"
        style={{ background: LEVEL_COLOR[level] }}
      />
      <div
        className="absolute left-[3px] right-0 top-0 h-[320px] pointer-events-none"
        style={{
          background: `linear-gradient(180deg, ${LEVEL_TINT[level]} 0%, transparent 100%)`,
        }}
      />
      <div className="relative">
        {stale && publishedAt ? <StaleBanner publishedAt={publishedAt} /> : null}
        <NodePanelHeader node={node} issuedAt={issuedAt} closeHref={closeHref} />
        <div className="px-6 py-5 flex flex-col gap-[22px]">
          {payload ? (
            <>
              <AllocationGauge allocation={payload.allocation} level={level} />
              <FanChart payload={payload} />
              <StressTimeline points={payload.stress_timeline} />
              <EnsembleSpread spread={payload.ensemble_spread} />
              <DataCenterList items={payload.data_centers} />
            </>
          ) : (
            <div className="rounded-md border border-stress-amber/30 bg-stress-amber/[0.06] p-3 text-[12.5px] text-text-primary">
              Forecast data unavailable for this node. Try again later.
            </div>
          )}
        </div>
        <div className="px-6 pb-5 pt-2.5 font-mono text-[11px] text-text-tertiary border-t border-border">
          Methodology
        </div>
      </div>
    </aside>
  );
}
