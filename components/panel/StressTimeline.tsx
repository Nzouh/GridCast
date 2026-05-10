import type { StressTimelinePoint } from '@/lib/types';

function color(probability: number): string {
  if (probability < 0.2) return 'bg-stress-green';
  if (probability < 0.5) return 'bg-stress-amber';
  return 'bg-stress-red';
}

export function StressTimeline({ points }: { points: StressTimelinePoint[] }) {
  return (
    <section>
      <div className="flex items-end justify-between mb-2">
        <div className="text-[10px] uppercase tracking-wider text-text-tertiary">Stress timeline</div>
        <div className="text-[11px] text-text-tertiary">hourly probability</div>
      </div>
      <div className="grid grid-cols-[repeat(120,minmax(0,1fr))] gap-px h-8 rounded overflow-hidden bg-black/[0.04] border border-black/5">
        {points.map((point) => (
          <div
            key={point.hour_offset}
            className={color(point.stress_probability)}
            style={{ opacity: 0.28 + point.stress_probability * 0.72 }}
            title={`h+${point.hour_offset}: ${Math.round(point.stress_probability * 100)}%`}
          />
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-text-tertiary">
        <span>now</span>
        <span>5d</span>
        <span>10d</span>
      </div>
    </section>
  );
}
