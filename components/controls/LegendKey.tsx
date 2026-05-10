export function LegendKey() {
  const items = [
    { color: 'oklch(0.66 0.16 150)', label: 'Stable' },
    { color: 'oklch(0.78 0.16 78)', label: 'Elevated' },
    { color: 'oklch(0.62 0.21 27)', label: 'Stressed' },
  ];
  return (
    <div className="absolute left-4 bottom-4 z-10 bg-white/95 backdrop-blur-md border border-border rounded-lg px-3 py-2 shadow-sm">
      <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-text-tertiary mb-1.5">
        Stress level
      </div>
      <div className="flex flex-col gap-1">
        {items.map((it) => (
          <div key={it.label} className="flex items-center gap-2 text-[12px] text-text-primary">
            <span className="inline-block w-2 h-2 rounded-full" style={{ background: it.color }} />
            {it.label}
          </div>
        ))}
      </div>
    </div>
  );
}
