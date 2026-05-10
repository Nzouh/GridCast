'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useTransition } from 'react';

export type GridFilter = 'target' | 'all';

export function GridFilterToggle({ filter }: { filter: GridFilter }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const setFilter = (next: GridFilter) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === 'target') {
      params.delete('filter');
    } else {
      params.set('filter', 'all');
    }
    const qs = params.toString();
    startTransition(() => {
      router.push(qs ? `/?${qs}` : '/');
    });
  };

  const targetActive = filter === 'target';

  return (
    <div
      className="inline-flex items-center gap-1 text-[13px] text-text-secondary"
      title="Show only the production grids GridCast actively forecasts."
    >
      <span>Target Grids</span>
      <div
        role="group"
        aria-label="Target Grids filter"
        className="inline-flex rounded border border-black/10 overflow-hidden"
      >
        <button
          type="button"
          aria-pressed={targetActive}
          disabled={isPending}
          onClick={() => setFilter('target')}
          className={
            'px-2 py-1 text-[12px] transition-colors ' +
            (targetActive
              ? 'bg-brand text-white'
              : 'bg-white text-text-secondary hover:text-text-primary')
          }
        >
          On
        </button>
        <button
          type="button"
          aria-pressed={!targetActive}
          disabled={isPending}
          onClick={() => setFilter('all')}
          className={
            'px-2 py-1 text-[12px] border-l border-black/10 transition-colors ' +
            (!targetActive
              ? 'bg-brand text-white'
              : 'bg-white text-text-secondary hover:text-text-primary')
          }
        >
          Off
        </button>
      </div>
    </div>
  );
}
