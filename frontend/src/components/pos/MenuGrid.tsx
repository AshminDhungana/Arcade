import type { MenuItem } from '@/types/pos';
import { MenuItemCard } from './MenuItemCard';
import { RefreshCw } from 'lucide-react';

interface MenuGridProps {
  items: MenuItem[] | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  onAddItem: (menuItemId: string) => void;
  inventoryEnabled: boolean;
}

/** Responsive grid of menu item cards, grouped by category. */
export function MenuGrid({
  items,
  isLoading,
  isError,
  onRetry,
  onAddItem,
  inventoryEnabled,
}: MenuGridProps) {
  // Loading skeleton
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3" role="status" aria-label="Loading menu">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-32 animate-pulse rounded-xl border border-slate-700/50 bg-slate-800/50"
          />
        ))}
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-red-800/50 bg-red-900/10 p-8 text-center">
        <p className="text-sm font-medium text-red-400">Failed to load menu</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 inline-flex items-center gap-2 rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-600"
        >
          <RefreshCw className="h-4 w-4" />
          Retry
        </button>
      </div>
    );
  }

  // Empty state
  if (!items || items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-slate-700/30 bg-slate-800/30 p-8 text-center">
        <div className="mb-3 rounded-full bg-slate-700/50 p-3">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </div>
        <p className="text-sm text-slate-400">No menu items configured</p>
      </div>
    );
  }

  // Group items by category
  const grouped = groupByCategory(items);

  return (
    <div className="space-y-5 overflow-y-auto pr-1" style={{ maxHeight: 'calc(100vh - 180px)' }}>
      {grouped.map(({ category, items: categoryItems }) => (
        <section key={category} aria-label={`Category: ${category}`}>
          <h3 className="mb-2.5 text-xs font-semibold uppercase tracking-wider text-slate-400">
            {category}
          </h3>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
            {categoryItems.map((item) => (
              <MenuItemCard
                key={item.id}
                item={item}
                onClick={() => onAddItem(item.id)}
                inventoryEnabled={inventoryEnabled}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Grouping helper
// ---------------------------------------------------------------------------

interface CategoryGroup {
  category: string;
  items: MenuItem[];
}

function groupByCategory(items: MenuItem[]): CategoryGroup[] {
  const map = new Map<string, MenuItem[]>();
  for (const item of items) {
    const cat = item.category ?? 'Uncategorized';
    const existing = map.get(cat);
    if (existing) {
      existing.push(item);
    } else {
      map.set(cat, [item]);
    }
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([category, items]) => ({ category, items }));
}
