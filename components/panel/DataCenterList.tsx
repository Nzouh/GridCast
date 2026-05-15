import type { DataCenter } from '@/lib/types';
import { DataCenterCard } from './DataCenterCard';

export function DataCenterList({ items }: { items: DataCenter[] }) {
  return (
    <section data-gc-tutorial="datacenters">
      <div className="gc-label mb-2">
        Co-located data centres
      </div>
      <div className="flex flex-col gap-2">
        {items.map((dc) => (
          <DataCenterCard key={dc.id} dc={dc} />
        ))}
      </div>
    </section>
  );
}
