import Link from 'next/link';
import { stressLevel } from '@/lib/formulas';
import type { Node } from '@/lib/types';

const CHIP: Record<'green' | 'amber' | 'red', { bg: string; text: string; label: string }> = {
  green: { bg: 'rgba(22,163,74,0.10)', text: 'oklch(0.50 0.15 150)', label: 'stable' },
  amber: { bg: 'rgba(245,158,11,0.12)', text: 'oklch(0.55 0.15 78)', label: 'elevated' },
  red: { bg: 'rgba(220,38,38,0.10)', text: 'oklch(0.50 0.20 27)', label: 'stressed' },
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
    <div className="px-6 pt-[22px] pb-4 border-b border-border">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-[24px] font-semibold tracking-[-0.02em] text-text-primary leading-[1.15]">
            {node.name}
          </h1>
          <div className="mt-1 font-mono text-[12.5px] text-text-secondary">
            {node.iso} · {node.state} · BA: {node.ba_code}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span
            className="inline-flex items-center gap-1.5 rounded px-2 py-1 font-mono text-[10.5px] font-semibold uppercase tracking-[0.08em]"
            style={{ background: chip.bg, color: chip.text }}
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
        <div className="mt-3 font-mono text-[11px] text-text-tertiary tabular-nums">
          Forecast issued {formatIssued(issuedAt)}
        </div>
      ) : null}
    </div>
  );
}
