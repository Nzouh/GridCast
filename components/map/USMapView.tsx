'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { geoAlbersUsa, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import type { Topology, GeometryCollection } from 'topojson-specification';
import type { Node } from '@/lib/types';
import { stressLevel } from '@/lib/formulas';

const T = {
  green: 'oklch(0.66 0.16 150)',
  amber: 'oklch(0.78 0.16 78)',
  red: 'oklch(0.62 0.21 27)',
  text: '#0B0F19',
  secondary: '#6B7280',
  tertiary: '#9CA3AF',
  panel: '#F7F8FA',
  border: '#ECEEF2',
  mapBg: '#FAFBFC',
  stateStroke: 'rgba(11,15,25,0.10)',
  fontMono: 'var(--font-jbmono), "JetBrains Mono", ui-monospace, monospace',
  fontDisplay: 'var(--font-inter), Inter, system-ui, sans-serif',
};

type Viewport = { scale: number; tx: number; ty: number };

type Props = {
  nodes: Node[];
  selectedId: string | null;
  panelOpen: boolean;
  replayNodeId?: string | null;
};

export function USMapView({ nodes, selectedId, panelOpen, replayNodeId }: Props) {
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 800, h: 500 });
  const [statePaths, setStatePaths] = useState<string[]>([]);
  const [projection, setProjection] = useState<ReturnType<typeof geoAlbersUsa> | null>(null);
  const [viewport, setViewport] = useState<Viewport>({ scale: 1, tx: 0, ty: 0 });
  const [hoverNode, setHoverNode] = useState<string | null>(null);
  const dragRef = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const e = entries[0];
      setSize({ w: e.contentRect.width, h: e.contentRect.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (size.w < 50) return;
    fetch('https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json')
      .then((r) => r.json())
      .then((topo: Topology) => {
        const states = feature(topo, topo.objects['states'] as GeometryCollection);
        const proj = geoAlbersUsa().fitSize([size.w, size.h], states);
        const pathFn = geoPath(proj);
        setProjection(() => proj);
        setStatePaths((states.features as GeoJSON.Feature[]).map((f) => pathFn(f) ?? ''));
      })
      .catch(() => {});
  }, [size.w, size.h]);

  function projectNode(node: Node): { x: number; y: number } | null {
    if (!projection) return null;
    const p = projection([node.lon, node.lat]);
    return p ? { x: p[0], y: p[1] } : null;
  }

  const onWheel = useCallback((e: WheelEvent) => {
    e.preventDefault();
    const delta = -e.deltaY * 0.0014;
    setViewport((vp) => {
      const newScale = Math.max(0.85, Math.min(3.5, vp.scale * (1 + delta)));
      const r = containerRef.current!.getBoundingClientRect();
      const cx = e.clientX - r.left;
      const cy = e.clientY - r.top;
      const dx = (cx - vp.tx) * (newScale / vp.scale - 1);
      const dy = (cy - vp.ty) * (newScale / vp.scale - 1);
      return { scale: newScale, tx: vp.tx - dx, ty: vp.ty - dy };
    });
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [onWheel]);

  function onDown(e: React.MouseEvent) {
    if ((e.target as HTMLElement).dataset.node) return;
    dragRef.current = { x: e.clientX, y: e.clientY, tx: viewport.tx, ty: viewport.ty };
  }
  function onMove(e: React.MouseEvent) {
    if (!dragRef.current) return;
    setViewport((vp) => ({
      ...vp,
      tx: dragRef.current!.tx + (e.clientX - dragRef.current!.x),
      ty: dragRef.current!.ty + (e.clientY - dragRef.current!.y),
    }));
  }
  function onUp() { dragRef.current = null; }

  const effectiveSelected = replayNodeId ?? selectedId;

  return (
    <div
      ref={containerRef}
      onMouseDown={onDown} onMouseMove={onMove} onMouseUp={onUp} onMouseLeave={onUp}
      style={{
        position: 'absolute', inset: 0, background: T.mapBg, overflow: 'hidden',
        cursor: dragRef.current ? 'grabbing' : 'grab',
      }}
    >
      {/* Atmospheric gradient */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: `
          radial-gradient(ellipse 50% 60% at 22% 50%, oklch(0.92 0.04 235) 0%, transparent 65%),
          radial-gradient(ellipse 45% 55% at 70% 65%, oklch(0.93 0.05 50) 0%, transparent 60%),
          radial-gradient(ellipse 35% 45% at 88% 35%, oklch(0.94 0.04 25) 0%, transparent 55%),
          linear-gradient(180deg, oklch(0.99 0.005 230) 0%, oklch(0.97 0.008 80) 100%)
        `,
      }} />

      <svg
        viewBox={`0 0 ${size.w} ${size.h}`}
        preserveAspectRatio="none"
        style={{
          position: 'absolute', inset: 0,
          transform: `translate(${viewport.tx}px, ${viewport.ty}px) scale(${viewport.scale})`,
          transformOrigin: '0 0',
        }}
      >
        {/* State paths */}
        {statePaths.map((d, i) => (
          <path key={i} d={d}
                fill="transparent"
                stroke={T.stateStroke}
                strokeWidth="0.7"
                strokeLinejoin="round" />
        ))}

        {/* Node markers */}
        {nodes.map((n) => {
          const p = projectNode(n);
          if (!p) return null;
          const level = stressLevel(n.stress_probability);
          const color = level === 'red' ? T.red : level === 'amber' ? T.amber : T.green;
          const isSel = effectiveSelected === n.id;
          const isOther = effectiveSelected !== null && !isSel;
          const isHover = hoverNode === n.id;
          const r = 6;

          return (
            <g key={n.id} data-node="1"
               style={{ cursor: 'pointer' }}
               onClick={(e) => {
                 e.stopPropagation();
                 if (replayNodeId) return;
                 router.push(`/?node=${n.id}`);
               }}
               onMouseEnter={() => setHoverNode(n.id)}
               onMouseLeave={() => setHoverNode(null)}
               opacity={isOther ? 0.35 : 1}>
              {/* Pulse halo for stressed nodes */}
              {level === 'red' && (
                <circle cx={p.x} cy={p.y} r={r * 2.4} fill={color} opacity="0.18">
                  <animate attributeName="r" values={`${r * 1.8};${r * 3.2};${r * 1.8}`}
                           dur="2.4s" repeatCount="indefinite" />
                  <animate attributeName="opacity" values="0.28;0.04;0.28"
                           dur="2.4s" repeatCount="indefinite" />
                </circle>
              )}
              {/* Selection ring */}
              {isSel && (
                <circle cx={p.x} cy={p.y} r={r + 6} fill="none"
                        stroke={color} strokeWidth="1.5" opacity="0.7" />
              )}
              {/* Soft halo */}
              <circle cx={p.x} cy={p.y} r={r + 3} fill={color} opacity="0.25" />
              {/* Dot */}
              <circle cx={p.x} cy={p.y} r={r} fill={color} stroke="#fff" strokeWidth="1.5" />
              {/* Label on hover or selection */}
              {(isHover || isSel) && (
                <g transform={`translate(${p.x}, ${p.y})`}>
                  <g transform={`translate(${r + 8}, -2)`}>
                    <text x="0" y="0" fontSize="10.5"
                          fontFamily={T.fontDisplay}
                          fill={T.text} fontWeight="600">{n.name}</text>
                    <text x="0" y="11" fontSize="9" fontFamily={T.fontMono}
                          fill={T.tertiary}>
                      {n.iso} · {Math.round((1 - n.stress_probability) * 100)}%
                    </text>
                  </g>
                </g>
              )}
            </g>
          );
        })}
      </svg>

      {/* Reset control */}
      <div style={{
        position: 'absolute', left: 16, bottom: 16,
        display: 'flex', alignItems: 'center', gap: 6,
        fontFamily: T.fontMono, fontSize: 10, color: T.secondary,
      }}>
        <button
          onClick={() => setViewport({ scale: 1, tx: 0, ty: 0 })}
          style={{
            background: T.panel, border: `1px solid ${T.border}`,
            borderRadius: 6, padding: '5px 10px', cursor: 'pointer',
            color: T.secondary, fontFamily: T.fontMono, fontSize: 10,
          }}
        >
          RESET
        </button>
        <span style={{ opacity: 0.6 }}>SCROLL · ZOOM</span>
      </div>

      {/* Legend */}
      <div style={{
        position: 'absolute',
        right: panelOpen ? 436 : 16,
        bottom: 16,
        display: 'flex', gap: 14,
        fontFamily: T.fontMono, fontSize: 10.5, color: T.secondary,
        background: 'rgba(255,255,255,0.85)',
        backdropFilter: 'blur(6px)',
        padding: '8px 12px', borderRadius: 6, border: `1px solid ${T.border}`,
        transition: 'right 280ms cubic-bezier(.2,.7,.3,1)',
      }}>
        {([['green', T.green, 'STABLE'], ['amber', T.amber, 'ELEVATED'], ['red', T.red, 'STRESSED']] as const).map(([k, c, l]) => (
          <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 7, height: 7, borderRadius: 7, background: c, display: 'block' }} />
            {l}
          </div>
        ))}
      </div>
    </div>
  );
}
