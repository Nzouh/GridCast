export function DataSourceFooter() {
  return (
    <footer className="flex items-center justify-between px-6 h-10 border-t border-black/5 bg-white text-[12px] text-text-secondary">
      <div>Data: EIA, Open-Meteo, Grid Status.</div>
      <div className="flex items-center gap-4">
<span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded border border-black/10 text-text-secondary">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-brand" />
          Built on IBM Cloud
        </span>
      </div>
    </footer>
  );
}
