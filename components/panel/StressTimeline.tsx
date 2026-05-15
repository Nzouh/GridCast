'use client';

import { useState } from 'react';
import type { StressTimelinePoint } from '@/lib/types';

function color(probability: number): string {
  if (probability < 0.2) return 'oklch(0.66 0.16 150)';
  if (probability < 0.5) return 'oklch(0.78 0.16 78)';
  return 'oklch(0.62 0.21 27)';
}

export function StressTimeline({ points }: { points: StressTimelinePoint[] }) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  return (
    <section data-gc-tutorial="stress">
      <div className="gc-section-head">
        <span>Stress timeline</span>
        <span>hourly probability</span>
      </div>
      <div
        className="grid gap-px h-[30px] rounded overflow-hidden bg-[#0B0F1908] border border-border cursor-crosshair"
        style={{ gridTemplateColumns: `repeat(${points.length}, minmax(0, 1fr))` }}
        onMouseMove={(event) => {
          const bounds = event.currentTarget.getBoundingClientRect();
          const nextIndex = Math.max(
            0,
            Math.min(
              points.length - 1,
              Math.floor(((event.clientX - bounds.left) / bounds.width) * points.length),
            ),
          );
          setHoverIndex(nextIndex);
        }}
        onMouseLeave={() => setHoverIndex(null)}
      >
        {points.map((point, index) => (
          <div
            key={point.hour_offset}
            style={{
              background: color(point.stress_probability),
              opacity: 0.35 + point.stress_probability * 0.65,
              transform: hoverIndex === index ? 'scaleY(1.08)' : 'scaleY(1)',
              transformOrigin: 'bottom',
              transition: 'transform 120ms',
            }}
            title={`h+${point.hour_offset}: ${Math.round(point.stress_probability * 100)}%`}
          />
        ))}
      </div>
      <div className="mt-1.5 flex justify-between font-mono text-[10.5px] text-text-tertiary tabular-nums">
        <span>
          {hoverIndex !== null
            ? `+${points[hoverIndex].hour_offset}h - ${Math.round(points[hoverIndex].stress_probability * 100)}% probability`
            : 'now'}
        </span>
        <span>5d</span>
        <span>10d</span>
      </div>
    </section>
  );
}
