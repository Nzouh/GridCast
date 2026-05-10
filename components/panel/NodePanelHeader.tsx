import Link from 'next/link';
import { stressLevel } from '@/lib/formulas';
import type { Node } from '@/lib/types';

const CHIP: Record<'green' | 'amber' | 'red', { bg: string; text: string; label: string }> = {
  green: { bg: 'bg-stress-green/10', text: 'text-stress-green', label: 'stable' },
  amber: { bg: 'bg-stress-amber/10', text: 'text-stress-amber', label: 'elevated' },
  red: { bg: 'bg-stress-red/10', text: 'text-stress-red', label: 'stressed' },
};

function formatIssued(iso: string): string {
  try {
    const d = new Date(iso);
    const time = d.toLocaleString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
      hour12: false,
    });
    const date = d.toLocaleDateString('en-US', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: 'UTC',
    });
    return `${time} UTC · ${date}`;
  } catch {
    return iso;
  }
}

export function NodePanelHeader({
  node,
  issuedAt,
  closeHref,
}: {
  node: Node;
  issuedAt: string | null;
  closeHref: string;
}) {
  const level = stressLevel(node.stress_probability);
  const chip = CHIP[level];

  return (
    <div className="px-6 pt-6 pb-4 border-b border-black/5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-[26px] font-semibold tracking-tight text-text-primary leading-tight">
            {node.name}
          </h1>
          <div className="mt-1 text-[13px] text-text-secondary">
            {node.iso} · {node.state} · BA: {node.ba_code}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span
            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-medium uppercase tracking-wider ${chip.bg} ${chip.text}`}
          >
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-current" />
            {chip.label}
          </span>
          <Link
            href={closeHref}
            aria-label="Close panel"
            className="inline-flex items-center justify-center w-7 h-7 rounded text-text-tertiary hover:bg-black/5 hover:text-text-primary"
          >
            ×
          </Link>
        </div>
      </div>
      {issuedAt ? (
        <div className="mt-3 text-[11px] text-text-tertiary">
          Forecast issued {formatIssued(issuedAt)}
        </div>
      ) : null}
    </div>
  );
}
