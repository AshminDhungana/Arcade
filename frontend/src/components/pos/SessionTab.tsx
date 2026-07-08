import type { MenuItem, SessionPOSItem } from '@/types/pos';
import { formatPaise } from '@/hooks/useFormatPaise';
import { TabItemRow } from './TabItemRow';
import { RefreshCw, ShoppingCart } from 'lucide-react';

interface SessionTabProps {
  items: SessionPOSItem[] | undefined;
  menuItems: MenuItem[] | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  onAdd: (menuItemId: string) => void;
  onRemoveOne: (posItemId: string, sessionId: string) => void;
  onRemoveAll: (menuItemId: string, sessionId: string, posItemIds: string[]) => void;
  isMutating: boolean;
}

/** Running list of POS items added to this session, with quantity grouping. */
export function SessionTab({
  items,
  menuItems,
  isLoading,
  isError,
  onRetry,
  onAdd,
  onRemoveOne,
  onRemoveAll,
  isMutating,
}: SessionTabProps) {
  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2" role="status" aria-label="Loading session items">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="h-16 animate-pulse rounded-lg border border-slate-700/50 bg-slate-800/50"
          />
        ))}
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-red-800/50 bg-red-900/10 p-6 text-center">
        <p className="text-sm font-medium text-red-400">Failed to load items</p>
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

  // Group items by menu_item_id
  const grouped = groupItems(items ?? []);

  // Empty state
  if (grouped.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-slate-700/30 bg-slate-800/30 p-8 text-center">
        <div className="mb-3 rounded-full bg-slate-700/50 p-3">
          <ShoppingCart className="h-6 w-6 text-slate-500" />
        </div>
        <p className="text-sm text-slate-400">No items added yet</p>
        <p className="mt-1 text-xs text-slate-500">Click menu items to add them</p>
      </div>
    );
  }

  // Build a name lookup from menu items
  const menuMap = new Map(menuItems?.map((m) => [m.id, m.name]) ?? []);

  // Calculate subtotal
  const subtotal = grouped.reduce(
    (sum, g) => sum + g.unitPricePaise * g.totalQuantity,
    0,
  );

  return (
    <div className="flex h-full flex-col">
      {/* Items list */}
      <div className="flex-1 space-y-2 overflow-y-auto pr-1" style={{ maxHeight: 'calc(100vh - 280px)' }}>
        {grouped.map((g) => (
          <TabItemRow
            key={g.menuItemId}
            itemName={menuMap.get(g.menuItemId) ?? 'Unknown Item'}
            quantity={g.totalQuantity}
            unitPricePaise={g.unitPricePaise}
            onIncrement={() => onAdd(g.menuItemId)}
            onDecrement={() => {
              // Remove the most recent row
              const lastRow = g.rowIds[g.rowIds.length - 1];
              if (lastRow && items?.[0]?.session_id) {
                onRemoveOne(lastRow, items[0].session_id);
              }
            }}
            onRemoveAll={() => {
              if (items?.[0]?.session_id) {
                onRemoveAll(g.menuItemId, items[0].session_id, g.rowIds);
              }
            }}
            isMutating={isMutating}
          />
        ))}
      </div>

      {/* Subtotal */}
      <div className="mt-4 border-t border-slate-700 pt-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-slate-300">Subtotal</span>
          <span className="text-lg font-bold text-white">{formatPaise(subtotal)}</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Grouping helper
// ---------------------------------------------------------------------------

interface GroupedItem {
  menuItemId: string;
  unitPricePaise: number;
  totalQuantity: number;
  /** Backend row IDs for this menu item (needed for removal). */
  rowIds: string[];
}

function groupItems(items: SessionPOSItem[]): GroupedItem[] {
  const map = new Map<string, GroupedItem>();
  for (const item of items) {
    const existing = map.get(item.menu_item_id);
    if (existing) {
      existing.totalQuantity += item.quantity;
      existing.rowIds.push(item.id);
    } else {
      map.set(item.menu_item_id, {
        menuItemId: item.menu_item_id,
        unitPricePaise: item.unit_price_paise,
        totalQuantity: item.quantity,
        rowIds: [item.id],
      });
    }
  }
  return Array.from(map.values());
}
