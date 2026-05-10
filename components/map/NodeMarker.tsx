'use client';

import { Marker } from 'react-map-gl/mapbox';
import { useRouter } from 'next/navigation';
import { stressLevel } from '@/lib/formulas';
import type { Node } from '@/lib/types';

const COLOR: Record<'green' | 'amber' | 'red', string> = {
  green: 'oklch(0.66 0.16 150)',
  amber: 'oklch(0.78 0.16 78)',
  red: 'oklch(0.62 0.21 27)',
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
  const opacity = isDimmed ? 0.4 : 1;
  const size = 36;
  const dot = 16;
  const centered = (diameter: number) => ({
    width: diameter,
    height: diameter,
    left: (size - diameter) / 2,
    top: (size - diameter) / 2,
  });

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
        className="group relative cursor-pointer"
        style={{
          width: size,
          height: size,
          opacity,
          transition: 'opacity 220ms ease',
        }}
      >
        <span
          className="absolute rounded-full"
          style={{
            ...centered(dot),
            background: fill,
            animation: PULSE[level],
            transformOrigin: 'center',
          }}
        />
        <span
          className="absolute rounded-full"
          style={{ ...centered(dot + 6), background: fill, opacity: 0.18 }}
        />
        {isSelected ? (
          <>
            <span
              className="absolute rounded-full"
              style={{
                ...centered(dot + 16),
                border: `1.5px solid ${fill}`,
                opacity: 0.55,
              }}
            />
            <span
              className="absolute rounded-full"
              style={{
                ...centered(dot + 8),
                border: `1px solid ${fill}`,
                opacity: 0.85,
              }}
            />
          </>
        ) : (
          <span
            className="absolute hidden rounded-full group-hover:block"
            style={{
              ...centered(dot + 10),
              border: `1px solid ${fill}`,
              opacity: 0.45,
            }}
          />
        )}
        <span
          className="absolute rounded-full"
          style={{
            ...centered(dot),
            background: isSelected ? '#ffffff' : fill,
            border: `${isSelected ? 2.2 : 2}px solid ${isSelected ? fill : '#ffffff'}`,
            boxShadow: '0 1px 3px rgba(0,0,0,0.22)',
          }}
        />
        {isSelected ? (
          <span
            className="absolute rounded-full"
            style={{ ...centered(dot * 0.45), background: fill }}
          />
        ) : null}
      </button>
    </Marker>
  );
}
