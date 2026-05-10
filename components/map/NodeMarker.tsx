'use client';

import { Marker } from 'react-map-gl/mapbox';
import { useRouter } from 'next/navigation';
import { stressLevel } from '@/lib/formulas';
import type { Node } from '@/lib/types';

const COLOR: Record<'green' | 'amber' | 'red', string> = {
  green: '#16A34A',
  amber: '#F59E0B',
  red: '#DC2626',
};

const PULSE: Record<'green' | 'amber' | 'red', string> = {
  green: 'gc-pulse-green 3.2s ease-out infinite',
  amber: 'gc-pulse-amber 2.4s ease-out infinite',
  red: 'gc-pulse 1.8s ease-out infinite',
};

export function NodeMarker({
  node,
  isSelected,
  isDimmed,
}: {
  node: Node;
  isSelected: boolean;
  isDimmed: boolean;
}) {
  const router = useRouter();
  const level = stressLevel(node.stress_probability);
  const fill = COLOR[level];
  const opacity = isDimmed ? 0.45 : 1;
  const ring = isSelected ? `0 0 0 4px ${fill}33, 0 0 0 1px ${fill}` : 'none';

  return (
    <Marker
      longitude={node.lon}
      latitude={node.lat}
      anchor="center"
      onClick={(e) => {
        e.originalEvent.stopPropagation();
        router.push(`/?node=${node.id}`);
      }}
    >
      <button
        type="button"
        aria-label={`${node.name} — ${level} stress`}
        className="relative cursor-pointer flex items-center justify-center"
        style={{ width: 24, height: 24, opacity }}
      >
        <span
          className="absolute inset-0 rounded-full"
          style={{ background: fill, animation: PULSE[level] }}
        />
        <span
          className="relative inline-block rounded-full"
          style={{
            width: 16,
            height: 16,
            background: fill,
            border: '2.5px solid white',
            boxShadow: ring === 'none' ? '0 1px 3px rgba(0,0,0,0.22)' : ring,
          }}
        />
      </button>
    </Marker>
  );
}
