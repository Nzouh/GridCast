import { ReplaySelector } from '../controls/ReplaySelector';
import { GridFilterToggle, type GridFilter } from '../controls/GridFilterToggle';
import type { ReplayId } from '@/lib/dataSource';

export function SiteHeader({
  replayId,
  filter,
}: {
  replayId: ReplayId | null;
  filter: GridFilter;
}) {
  return (
    <header className="flex items-center justify-between h-14 px-6 border-b border-black/5 bg-white">
      <div className="text-[18px] font-semibold tracking-tight text-brand">GridCast</div>
      <div className="flex items-center gap-5">
        {replayId === null ? <GridFilterToggle filter={filter} /> : null}
        <ReplaySelector activeReplay={replayId} />
      </div>
    </header>
  );
}
