export function LegendKey() {
  const items = [
    { color: 'bg-stress-green', label: 'Stable' },
    { color: 'bg-stress-amber', label: 'Elevated' },
    { color: 'bg-stress-red', label: 'Stressed' },
  ];
  return (
    <div className="absolute left-4 bottom-4 z-10 bg-white/95 backdrop-blur border border-black/5 rounded-md px-3 py-2 shadow-sm">
      <div className="text-[10px] uppercase tracking-wider text-text-tertiary mb-1.5">
        Stress level
      </div>
      <div className="flex flex-col gap-1">
        {items.map((it) => (
          <div key={it.label} className="flex items-center gap-2 text-[12px] text-text-primary">
            <span className={`inline-block w-2 h-2 rounded-full ${it.color}`} />
            {it.label}
          </div>
        ))}
      </div>
    </div>
  );
}
