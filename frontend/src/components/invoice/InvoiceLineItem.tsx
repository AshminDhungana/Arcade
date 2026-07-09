// frontend/src/components/invoice/InvoiceLineItem.tsx
import type { InvoiceLineItem } from '@/types/invoice';
import { formatPaise } from '@/hooks/useFormatPaise';

interface InvoiceLineItemProps {
  item: InvoiceLineItem;
}

/** Single line item row for invoice breakdown table. */
export function InvoiceLineItem({ item }: InvoiceLineItemProps) {
  const isDiscount =
    item.type === 'DISCOUNT' ||
    item.type === 'PROMOTION_DISCOUNT' ||
    item.type === 'LOYALTY_DISCOUNT';
  const isPackageCredit = item.type === 'PACKAGE_CREDIT';

  const rowClass = isDiscount
    ? 'text-red-400'
    : isPackageCredit
    ? 'text-emerald-400'
    : 'text-slate-300';

  // For display, use absolute value (the minus sign is handled in parent totals)
  const displayTotal = Math.abs(item.total_paise);
  const displayUnit = Math.abs(item.unit_price_paise);

  return (
    <tr className={rowClass}>
      <td className="px-3 py-2 text-sm">
        {item.description}
        {item.quantity > 1 && <span className="ml-2 text-slate-500">x{item.quantity}</span>}
      </td>
      <td className="px-3 py-2 text-sm text-right">{formatPaise(displayUnit)}</td>
      <td className="px-3 py-2 text-sm text-right font-medium">{formatPaise(displayTotal)}</td>
    </tr>
  );
}
