'use client';

import { useRouter } from 'next/navigation';
import { useTransition } from 'react';
import type { ReplayId } from '@/lib/dataSource';

const OPTIONS: { value: '' | ReplayId; label: string }[] = [
  { value: '', label: 'Live' },
  { value: 'texas-2021', label: 'Texas Winter Storm 2021' },
  { value: 'pjm-2023', label: 'PJM Summer 2023' },
];

export function ReplaySelector({ activeReplay }: { activeReplay: ReplayId | null }) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  return (
    <label className="inline-flex items-center gap-2 text-[13px] text-text-secondary">
      <span>Replay event</span>
      <select
        value={activeReplay ?? ''}
        disabled={isPending}
        onChange={(e) => {
          const value = e.target.value;
          startTransition(() => {
            router.push(value === '' ? '/' : `/?replay=${value}`);
          });
        }}
        className="text-text-primary bg-white border border-black/10 rounded px-2 py-1 hover:border-black/20 focus:outline-none focus:ring-2 focus:ring-brand/30"
      >
        {OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}
