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
        style={{ width: 16, height: 16, opacity }}
      >
        {level === 'red' ? (
          <span
            className="absolute inset-0 rounded-full"
            style={{
              background: fill,
              animation: 'gc-pulse 1.8s ease-out infinite',
            }}
          />
        ) : null}
        <span
          className="relative inline-block rounded-full"
          style={{
            width: 12,
            height: 12,
            background: fill,
            border: '2px solid white',
            boxShadow: ring === 'none' ? '0 1px 2px rgba(0,0,0,0.18)' : ring,
          }}
        />
      </button>
    </Marker>
  );
}
