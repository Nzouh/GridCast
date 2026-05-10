'use client';

import type { Allocation } from '@/lib/types';

const T = {
  text: '#0B0F19',
  secondary: '#6B7280',
  tertiary: '#9CA3AF',
  subtle: '#EEF1F5',
  brand: '#0F3D56',
  fontDisplay: 'var(--font-inter), Inter, system-ui, sans-serif',
  fontMono: 'var(--font-jbmono), "JetBrains Mono", ui-monospace, monospace',
};

export function AllocationGauge({ alloc }: { alloc: Allocation }) {
  return (
    <div style={{ padding: '20px 24px 14px' }}>
      <div style={{
        fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase',
        color: T.tertiary, fontWeight: 500, marginBottom: 6, fontFamily: T.fontDisplay,
      }}>
        Recommended allocation
      </div>
      <div style={{
        fontFamily: T.fontDisplay,
        fontSize: 92, lineHeight: 0.95, fontWeight: 500,
        letterSpacing: '-0.04em', color: T.text,
        display: 'flex', alignItems: 'baseline', gap: 4,
      }}>
        {alloc.pct}
        <span style={{ fontSize: 36, fontWeight: 400, color: T.secondary, letterSpacing: '-0.01em' }}>%</span>
      </div>
      <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ flex: 1, height: 4, borderRadius: 2, background: T.subtle, position: 'relative' }}>
          <div style={{
            position: 'absolute',
            left: `${alloc.pct_p50}%`,
            right: `${100 - alloc.pct_p10}%`,
            top: 0, bottom: 0,
            background: T.brand, borderRadius: 2, opacity: 0.85,
          }} />
          <div style={{
            position: 'absolute',
            left: `calc(${alloc.pct}% - 1px)`,
            top: -3, width: 2, height: 10,
            background: T.text,
          }} />
        </div>
        <div style={{
          fontFamily: T.fontMono, fontSize: 11, color: T.secondary,
          whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums',
        }}>
          p10–p90 · {alloc.pct_p50}–{alloc.pct_p10}%
        </div>
      </div>
    </div>
  );
}
