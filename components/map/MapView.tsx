'use client';

import 'mapbox-gl/dist/mapbox-gl.css';
import { Map } from 'react-map-gl/mapbox';
import { NodeMarker } from './NodeMarker';
import type { MapShellProps } from './MapShell';

const TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? '';

export function MapView({ nodes, selectedId, panelOpen }: MapShellProps) {
  if (!TOKEN) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-surface-panel">
        <div className="text-center max-w-sm px-6">
          <div className="text-[14px] text-text-secondary mb-1">Map disabled</div>
          <div className="text-[12px] text-text-tertiary">
            Set <code className="font-mono text-text-primary">NEXT_PUBLIC_MAPBOX_TOKEN</code> in
            <code className="font-mono text-text-primary"> .env.local</code> to enable the basemap.
          </div>
        </div>
      </div>
    );
  }

  return (
    <Map
      mapboxAccessToken={TOKEN}
      initialViewState={{
        longitude: -96,
        latitude: 39,
        zoom: 3.6,
      }}
      mapStyle="mapbox://styles/mapbox/light-v11"
      style={{ width: '100%', height: '100%' }}
      attributionControl={false}
      padding={panelOpen ? { top: 0, right: 420, bottom: 0, left: 0 } : undefined}
    >
      {nodes.map((n) => (
        <NodeMarker
          key={n.id}
          node={n}
          isSelected={n.id === selectedId}
          isDimmed={selectedId !== null && n.id !== selectedId}
        />
      ))}
    </Map>
  );
}
