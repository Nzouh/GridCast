import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';
import {
  getNodes,
  getForecast,
  getReplay,
  VALID_NODE_IDS,
  VALID_REPLAY_IDS,
} from '@/lib/dataSource';
import type { Node, ForecastResponse, ReplayResponse, DataSource } from '@/lib/types';
import { SiteHeader } from '@/components/shell/SiteHeader';
import { DataSourceFooter } from '@/components/shell/DataSourceFooter';
import { DesktopOnlyNotice } from '@/components/shell/DesktopOnlyNotice';
import { ReplayBanner } from '@/components/shell/ReplayBanner';
import { MapShell } from '@/components/map/MapShell';
import { NodePanel } from '@/components/panel/NodePanel';
import { LegendKey } from '@/components/controls/LegendKey';
import { TutorialPanel } from '@/components/tutorial/TutorialPanel';
import type { GridFilter } from '@/components/controls/GridFilterToggle';
import type { ReplayId, NodeId } from '@/lib/dataSource';

export const dynamic = 'force-dynamic';

const REPLAY_FOCUS: Record<ReplayId, NodeId> = {
  'texas-2021': 'ercot-houston',
  'pjm-2023': 'dominion-hub',
};

type SearchParams = { node?: string; replay?: string; filter?: string };

function isReplayId(v: string | undefined): v is ReplayId {
  return !!v && (VALID_REPLAY_IDS as readonly string[]).includes(v);
}

function isNodeId(v: string | undefined): v is NodeId {
  return !!v && (VALID_NODE_IDS as readonly string[]).includes(v);
}

function parseFilter(v: string | undefined): GridFilter {
  return v === 'target' ? 'target' : 'all';
}

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const replayParam = params.replay;
  const nodeParam = params.node;
  const filter: GridFilter = parseFilter(params.filter);

  const cookieStore = await cookies();
  const isFirstVisit = !cookieStore.has('gc_onboarding_done');

  if (replayParam && nodeParam) {
    redirect(`/?replay=${replayParam}`);
  }

  const replayId: ReplayId | null = isReplayId(replayParam) ? replayParam : null;
  let nodes: Node[] = [];
  let nodesSource: DataSource | null = null;
  let nodesPublishedAt: string | null = null;
  let stale = false;
  let nodesError = false;

  try {
    const r = await getNodes();
    nodes = r.data.nodes;
    nodesSource = r.data.source;
    nodesPublishedAt = r.data.published_at;
    stale = r.stale;
  } catch (error) {
    console.error('GridCast nodes load failed', error);
    nodesError = true;
  }

  let selectedNodeId: NodeId | null = null;
  if (replayId) {
    selectedNodeId = REPLAY_FOCUS[replayId];
  } else if (isNodeId(nodeParam)) {
    selectedNodeId = nodeParam;
  }

  let forecast: ForecastResponse | null = null;
  let replay: ReplayResponse | null = null;
  let detailPublishedAt: string | null = null;

  if (replayId) {
    try {
      const r = await getReplay(replayId);
      replay = r.data;
      detailPublishedAt = r.data.published_at;
      stale = stale || r.stale;
    } catch (error) {
      console.error(`GridCast replay load failed: ${replayId}`, error);
      // panel will render the unavailable state
    }
  } else if (selectedNodeId) {
    try {
      const r = await getForecast(selectedNodeId);
      forecast = r.data;
      detailPublishedAt = r.data.published_at;
      stale = stale || r.stale;
    } catch (error) {
      console.error(`GridCast forecast load failed: ${selectedNodeId}`, error);
      // ditto
    }
  }

  const selectedNode =
    selectedNodeId !== null ? nodes.find((n) => n.id === selectedNodeId) ?? null : null;
  const closeHref = replayId ? `/?replay=${replayId}` : '/';

  // Replay forces target-only display (filter UI is hidden during replay).
  const effectiveFilter: GridFilter = replayId ? 'target' : filter;
  const visibleNodes =
    effectiveFilter === 'target' ? nodes.filter((n) => n.is_live) : nodes;

  return (
    <>
      <DesktopOnlyNotice />
      <div className="hidden lg:flex flex-col h-screen bg-white text-text-primary">
        <SiteHeader replayId={replayId} filter={filter} />
        {replayId && replay ? (
          <ReplayBanner eventName={replay.event_name} issuedAt={replay.issued_at} />
        ) : null}
        <main className="flex-1 relative overflow-hidden">
          {nodesError ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center max-w-sm px-6">
                <div className="text-[14px] text-text-secondary mb-1">Grid data unavailable</div>
                <div className="text-[12px] text-text-tertiary">
                  Source: {nodesSource ?? 'unknown'}. Try again in a moment.
                </div>
              </div>
            </div>
          ) : (
            <>
              <MapShell
                nodes={visibleNodes}
                selectedId={selectedNodeId}
                panelOpen={selectedNode !== null}
              />
              <LegendKey />
              <TutorialPanel defaultOpen={isFirstVisit} forecast={forecast} />
              {selectedNode ? (
                <NodePanel
                  node={selectedNode}
                  forecast={forecast}
                  replay={replay}
                  closeHref={closeHref}
                  stale={stale}
                  publishedAt={detailPublishedAt ?? nodesPublishedAt}
                />
              ) : null}
            </>
          )}
        </main>
        <DataSourceFooter />
      </div>
    </>
  );
}
