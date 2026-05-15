import { ReplaySelector } from '../controls/ReplaySelector';
import { GridFilterToggle, type GridFilter } from '../controls/GridFilterToggle';
import { TutorialButton } from '../tutorial/TutorialButton';
import type { ReplayId } from '@/lib/dataSource';
import { PulseLogo } from './PulseLogo';

export function SiteHeader({
  replayId,
  filter,
}: {
  replayId: ReplayId | null;
  filter: GridFilter;
}) {
  return (
    <header className="flex items-center justify-between h-14 px-6 border-b border-border bg-white">
      <div className="flex items-center gap-2.5 text-brand">
        <PulseLogo size={27} className="shrink-0" />
        <div className="text-[18px] font-semibold tracking-[-0.028em]">Gridcast</div>
      </div>
      <div className="flex items-center gap-5">
        {replayId === null ? <GridFilterToggle filter={filter} /> : null}
        <ReplaySelector activeReplay={replayId} />
        <TutorialButton />
      </div>
    </header>
  );
}
