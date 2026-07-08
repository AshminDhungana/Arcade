import type { MenuItem } from '@/types/pos';
import { formatPaise } from '@/hooks/useFormatPaise';

interface MenuItemCardProps {
  item: MenuItem;
  onClick: () => void;
  inventoryEnabled: boolean;
}

/** Single menu item card with name, price, stock badge, and click-to-add. */
export function MenuItemCard({ item, onClick, inventoryEnabled }: MenuItemCardProps) {
  const isOutOfStock = item.stock_quantity !== null && item.stock_quantity === 0;
  const isDisabled = !item.is_available || isOutOfStock;

  // Stock badge logic (only when inventory tracking is ON)
  const stockBadge = getStockBadge(item, inventoryEnabled);

  return (
    <button
      type="button"
      onClick={isDisabled ? undefined : onClick}
      disabled={isDisabled}
      className={`
        group relative flex flex-col rounded-xl border p-4 text-left
        transition-all duration-200
        ${isDisabled
          ? 'cursor-not-allowed border-slate-700/50 bg-slate-800/40 opacity-50'
          : 'cursor-pointer border-slate-700 bg-slate-800 hover:border-blue-500/50 hover:bg-slate-750 hover:shadow-lg hover:shadow-blue-500/5 active:scale-[0.98]'
        }
      `}
      aria-label={`${item.name}, ${formatPaise(item.price_paise)}${isDisabled ? ', unavailable' : ''}`}
    >
      {/* Category tag */}
      {item.category && (
        <span className="mb-2 inline-block self-start rounded-full bg-slate-700/60 px-2.5 py-0.5 text-xs font-medium text-slate-300">
          {item.category}
        </span>
      )}

      {/* Name */}
      <h4 className={`text-sm font-semibold ${isDisabled ? 'text-slate-500' : 'text-white'}`}>
        {item.name}
      </h4>

      {/* Price */}
      <p className={`mt-1 text-lg font-bold ${isDisabled ? 'text-slate-600 line-through' : 'text-emerald-400'}`}>
        {formatPaise(item.price_paise)}
      </p>

      {/* Stock badge */}
      {stockBadge && (
        <span
          className={`mt-2 inline-flex items-center gap-1 self-start rounded-full px-2 py-0.5 text-xs font-medium ${stockBadge.classes}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${stockBadge.dotClass}`} />
          {stockBadge.label}
        </span>
      )}

      {/* Hover add indicator */}
      {!isDisabled && (
        <div className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full bg-blue-500/0 text-blue-400 opacity-0 transition-all group-hover:bg-blue-500/20 group-hover:opacity-100">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
        </div>
      )}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Stock badge helper
// ---------------------------------------------------------------------------

interface StockBadgeInfo {
  label: string;
  classes: string;
  dotClass: string;
}

function getStockBadge(item: MenuItem, inventoryEnabled: boolean): StockBadgeInfo | null {
  if (!inventoryEnabled) return null;
  if (item.stock_quantity === null) return null; // unlimited stock

  if (item.stock_quantity === 0) {
    return {
      label: 'Out of Stock',
      classes: 'bg-red-500/10 text-red-400',
      dotClass: 'bg-red-400',
    };
  }

  if (
    item.low_stock_threshold !== null &&
    item.stock_quantity <= item.low_stock_threshold
  ) {
    return {
      label: `Low Stock (${item.stock_quantity} left)`,
      classes: 'bg-amber-500/10 text-amber-400',
      dotClass: 'bg-amber-400',
    };
  }

  return {
    label: 'In Stock',
    classes: 'bg-emerald-500/10 text-emerald-400',
    dotClass: 'bg-emerald-400',
  };
}
