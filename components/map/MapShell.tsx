'use client';

import dynamic from 'next/dynamic';
import type { Node } from '@/lib/types';

const MapView = dynamic(() => import('./MapView').then((m) => m.MapView), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 bg-surface-panel" aria-hidden />
  ),
});

export type MapShellProps = {
  nodes: Node[];
  selectedId: string | null;
  panelOpen: boolean;
};

export function MapShell(props: MapShellProps) {
  return <MapView {...props} />;
}
