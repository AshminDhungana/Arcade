import { formatPaise } from '@/hooks/useFormatPaise';
import { Minus, Plus, X, Loader2 } from 'lucide-react';

interface TabItemRowProps {
  itemName: string;
  quantity: number;
  unitPricePaise: number;
  onIncrement: () => void;
  onDecrement: () => void;
  onRemoveAll: () => void;
  isMutating: boolean;
}

/** Single row in the session tab: item name, qty stepper, line total, remove. */
export function TabItemRow({
  itemName,
  quantity,
  unitPricePaise,
  onIncrement,
  onDecrement,
  onRemoveAll,
  isMutating,
}: TabItemRowProps) {
  const lineTotal = unitPricePaise * quantity;

  return (
    <div className="group flex items-center gap-3 rounded-lg border border-slate-700/50 bg-slate-800/50 px-3 py-2.5 transition-colors hover:border-slate-600">
      {/* Item name */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-white">{itemName}</p>
        <p className="text-xs text-slate-400">
          {formatPaise(unitPricePaise)} each
        </p>
      </div>

      {/* Quantity stepper */}
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={onDecrement}
          disabled={isMutating}
          className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-700 text-slate-300 transition-colors hover:bg-slate-600 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
          aria-label={`Decrease ${itemName} quantity`}
        >
          <Minus className="h-3.5 w-3.5" />
        </button>

        <span className="flex h-7 w-8 items-center justify-center text-sm font-semibold text-white">
          {isMutating ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-400" />
          ) : (
            quantity
          )}
        </span>

        <button
          type="button"
          onClick={onIncrement}
          disabled={isMutating}
          className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-700 text-slate-300 transition-colors hover:bg-slate-600 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
          aria-label={`Increase ${itemName} quantity`}
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Line total */}
      <p className="w-20 text-right text-sm font-semibold text-emerald-400">
        {formatPaise(lineTotal)}
      </p>

      {/* Remove all button */}
      <button
        type="button"
        onClick={onRemoveAll}
        disabled={isMutating}
        className="flex h-7 w-7 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-red-500/10 hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-40"
        aria-label={`Remove all ${itemName}`}
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
