// frontend/src/components/invoice/InvoicePanel.tsx
import { formatPaise } from '@/hooks/useFormatPaise';
import type { Invoice } from '@/types/invoice';
import { formatDuration } from '@/utils/formatDuration';
import { InvoiceLineItem } from './InvoiceLineItem';
import { Clock, CreditCard, Receipt } from 'lucide-react';

interface InvoicePanelProps {
  invoice: Invoice;
  sessionDurationSeconds?: number;
}

/** Read-only invoice breakdown display component. */
export function InvoicePanel({ invoice, sessionDurationSeconds }: InvoicePanelProps) {
  // Separate different line items for summary
  const hasLineItems = invoice.line_items && invoice.line_items.length > 0;

  return (
    <div className="space-y-4">
      {/* Receipt Title Header */}
      <div className="flex items-center gap-2 border-b border-slate-700/50 pb-3">
        <Receipt className="h-5 w-5 text-blue-400" />
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
          Receipt Details
        </h3>
      </div>

      {/* Session duration card */}
      {sessionDurationSeconds !== undefined && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/40 border border-slate-700/50">
          <span className="text-sm text-slate-400 flex items-center gap-2">
            <Clock className="h-4 w-4 text-blue-400" />
            Duration
          </span>
          <span className="font-mono text-base font-bold text-white">
            {formatDuration(sessionDurationSeconds)}
          </span>
        </div>
      )}

      {/* Line Items Table */}
      {hasLineItems ? (
        <div className="overflow-hidden rounded-lg border border-slate-700/50 bg-slate-800/20">
          <table className="min-w-full divide-y divide-slate-700/50">
            <thead className="bg-slate-800/50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Description
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Rate
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Total
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 bg-transparent">
              {invoice.line_items.map((item) => (
                <InvoiceLineItem key={item.id} item={item} />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="py-4 text-center text-sm text-slate-500 italic">
          No line items in this invoice.
        </div>
      )}

      {/* Summary Totals */}
      <div className="space-y-2 border-t border-slate-800 pt-3">
        <div className="flex justify-between text-sm text-slate-400">
          <span>Time Charge</span>
          <span className="font-mono text-slate-200">
            {formatPaise(invoice.time_charge_paise)}
          </span>
        </div>

        {invoice.package_credit_used_paise > 0 && (
          <div className="flex justify-between text-sm text-emerald-400">
            <span>Package Credit Applied</span>
            <span className="font-mono font-medium">
              -{formatPaise(invoice.package_credit_used_paise)}
            </span>
          </div>
        )}

        {invoice.discount_paise > 0 && (
          <div className="flex justify-between text-sm text-red-400">
            <span>Discounts</span>
            <span className="font-mono font-medium">
              -{formatPaise(invoice.discount_paise)}
            </span>
          </div>
        )}

        {invoice.pos_total_paise > 0 && (
          <div className="flex justify-between text-sm text-slate-400">
            <span>POS items total</span>
            <span className="font-mono text-slate-200">
              {formatPaise(invoice.pos_total_paise)}
            </span>
          </div>
        )}

        <div className="flex justify-between items-center text-base font-semibold text-white border-t border-slate-800 pt-2 mt-2">
          <span>Grand Total</span>
          <span className="font-mono text-lg text-emerald-400">
            {formatPaise(invoice.total_paise)}
          </span>
        </div>
      </div>

      {/* Payment Method Display */}
      {invoice.payment_method && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/20 border border-slate-700/30 text-sm">
          <span className="text-slate-400 flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-slate-400" />
            Payment Status
          </span>
          <PaymentMethodBadge method={invoice.payment_method} />
        </div>
      )}
    </div>
  );
}

// Helper Badge component
function PaymentMethodBadge({ method }: { method: 'CASH' | 'CARD' | 'WALLET' | 'PACKAGE' }) {
  const config = {
    CASH: { label: 'Cash Paid', icon: '💵', styles: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
    CARD: { label: 'Card Paid', icon: '💳', styles: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
    WALLET: { label: 'Wallet Deducted', icon: '👛', styles: 'bg-purple-500/10 text-purple-400 border-purple-500/20' },
    PACKAGE: { label: 'Package Drawdown', icon: '📦', styles: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  }[method];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${config.styles}`}
    >
      <span>{config.icon}</span>
      {config.label}
    </span>
  );
}
