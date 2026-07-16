import { useState } from 'react';
import { Printer, Loader2 } from 'lucide-react';
import {
  useUnprintedInvoices,
  useReprintInvoice,
  useMarkInvoicePrinted,
  printInvoicePdf,
} from '@/api/invoices';
import { useForceCloseUnprinted } from '@/api/sessions';
import { useAuthStore } from '@/store/authStore';
import { PinConfirmModal } from './PinConfirmModal';
import type { Invoice } from '@/types/invoice';

function formatMoney(paise: number): string {
  return `Rs. ${(paise / 100).toFixed(2)}`;
}

export function UnprintedInvoices() {
  const token = useAuthStore((s) => s.accessToken);
  const { data, isLoading } = useUnprintedInvoices();
  const reprint = useReprintInvoice();
  const markPrinted = useMarkInvoicePrinted();
  const forceClose = useForceCloseUnprinted();
  const [forceTarget, setForceTarget] = useState<Invoice | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <section className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
      </section>
    );
  }

  const rows = data ?? [];

  return (
    <section className="rounded-xl border border-amber-600/40 bg-slate-800 p-5">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-amber-400">
        Unprinted Invoices ({rows.length})
      </h2>

      {rows.length === 0 ? (
        <p className="text-sm text-slate-400">No unprinted invoices. 🎉</p>
      ) : (
        <ul className="space-y-3" role="list">
          {rows.map((inv) => (
            <li
              key={inv.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-700 bg-slate-900/50 p-3"
            >
              <div className="min-w-0">
                <p className="font-mono text-sm text-slate-200">#{inv.id.slice(0, 8)}</p>
                <p className="text-xs text-slate-400">
                  {formatMoney(inv.total_paise)} · {inv.print_status}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busyId === inv.id}
                  onClick={async () => {
                    setBusyId(inv.id);
                    try {
                      await reprint.mutateAsync(inv.id);
                    } finally {
                      setBusyId(null);
                    }
                  }}
                  className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700 cursor-pointer flex items-center gap-1"
                >
                  <Printer className="h-3.5 w-3.5" /> Reprint
                </button>
                <button
                  type="button"
                  disabled={busyId === inv.id}
                  onClick={async () => {
                    setBusyId(inv.id);
                    try {
                      await printInvoicePdf(inv.id, token);
                      await markPrinted.mutateAsync(inv.id);
                    } finally {
                      setBusyId(null);
                    }
                  }}
                  className="rounded-lg border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700 cursor-pointer flex items-center gap-1"
                >
                  <Printer className="h-3.5 w-3.5" /> PDF → Mark
                </button>
                <button
                  type="button"
                  onClick={() => setForceTarget(inv)}
                  className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-500 cursor-pointer"
                >
                  Force close
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <PinConfirmModal
        open={forceTarget !== null}
        title="Force close unprinted checkout"
        confirmLabel="Force close"
        isPending={forceClose.isPending}
        onClose={() => setForceTarget(null)}
        onConfirm={(pin, reason) => {
          if (!forceTarget) return;
          forceClose.mutate(
            { sessionId: forceTarget.session_id, pin, reason },
            {
              onSuccess: () => setForceTarget(null),
              onError: () => setForceTarget(null),
            },
          );
        }}
      />
    </section>
  );
}
