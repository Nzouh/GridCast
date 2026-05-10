import Link from 'next/link';

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      timeZone: 'UTC',
    });
  } catch {
    return iso;
  }
}

export function ReplayBanner({
  eventName,
  issuedAt,
}: {
  eventName: string;
  issuedAt: string;
}) {
  return (
    <div className="flex items-center justify-between px-6 py-2 bg-brand/[0.04] border-b border-brand/10 text-[12px]">
      <span className="text-text-primary">
        <span className="font-medium text-brand">Replay mode</span>
        <span className="text-text-tertiary mx-2">·</span>
        <span>{eventName} — forecast issued {formatDate(issuedAt)}, 10 days before peak event.</span>
      </span>
      <Link
        href="/"
        className="text-brand hover:underline"
      >
        Return to live →
      </Link>
    </div>
  );
}
