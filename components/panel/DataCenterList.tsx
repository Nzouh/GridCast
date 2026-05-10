import type { DataCenter } from '@/lib/types';
import { DataCenterCard } from './DataCenterCard';

export function DataCenterList({ items }: { items: DataCenter[] }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-text-tertiary mb-2">
        Co-located data centres
      </div>
      <div className="flex flex-col gap-2">
        {items.map((dc) => (
          <DataCenterCard key={dc.id} dc={dc} />
        ))}
      </div>
    </div>
  );
}
