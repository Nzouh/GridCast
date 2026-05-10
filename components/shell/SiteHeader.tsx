import { ReplaySelector } from '../controls/ReplaySelector';
import type { ReplayId } from '@/lib/dataSource';

export function SiteHeader({ replayId }: { replayId: ReplayId | null }) {
  return (
    <header className="flex items-center justify-between h-14 px-6 border-b border-black/5 bg-white">
      <div className="text-[18px] font-semibold tracking-tight text-brand">GridCast</div>
      <ReplaySelector activeReplay={replayId} />
    </header>
  );
}
