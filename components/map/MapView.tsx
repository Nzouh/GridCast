'use client';

import 'mapbox-gl/dist/mapbox-gl.css';
import { Map } from 'react-map-gl/mapbox';
import type { Map as MapboxMap } from 'mapbox-gl';
import { NodeMarker } from './NodeMarker';
import type { MapShellProps } from './MapShell';

const TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? '';

function setPaint(map: MapboxMap, layerId: string, property: string, value: string | number) {
  if (!map.getLayer(layerId)) return;
  try {
    map.setPaintProperty(layerId, property as Parameters<MapboxMap['setPaintProperty']>[1], value);
  } catch {
    // Mapbox styles differ by account/version; missing paint props are safe to ignore.
  }
}

function applySubtleEarthColor(map: MapboxMap) {
  setPaint(map, 'background', 'background-color', '#F7F3EA');
  setPaint(map, 'land', 'background-color', '#F7F3EA');
  setPaint(map, 'land', 'fill-color', '#F7F3EA');
  setPaint(map, 'landuse', 'fill-color', '#E7F1E2');
  setPaint(map, 'landuse', 'fill-opacity', 0.42);
  setPaint(map, 'national-park', 'fill-color', '#DDEED7');
  setPaint(map, 'national-park', 'fill-opacity', 0.48);
  setPaint(map, 'water', 'fill-color', '#D8ECF6');
  setPaint(map, 'waterway', 'line-color', '#B7DCE8');

  map.setFog({
    color: 'rgb(235, 244, 248)',
    'high-color': 'rgb(180, 211, 229)',
    'horizon-blend': 0.18,
    'space-color': 'rgb(248, 250, 252)',
    'star-intensity': 0,
  });
}

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
      projection={{ name: 'globe' }}
      style={{ width: '100%', height: '100%' }}
      attributionControl={false}
      padding={panelOpen ? { top: 0, right: 420, bottom: 0, left: 0 } : undefined}
      onLoad={(event) => applySubtleEarthColor(event.target)}
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
