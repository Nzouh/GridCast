'use client';

function formatPublishedAt(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
      hour12: false,
    }) + ' UTC';
  } catch {
    return iso;
  }
}

export function StaleBanner({ publishedAt }: { publishedAt: string }) {
  return (
    <div className="bg-stress-amber/10 border-b border-stress-amber/30 text-[12px] text-text-primary px-6 py-2">
      Showing data older than 25 hours — published {formatPublishedAt(publishedAt)}.
    </div>
  );
}
