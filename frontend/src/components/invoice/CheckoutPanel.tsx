// frontend/src/components/invoice/CheckoutPanel.tsx
import { useState, useCallback, useMemo } from 'react';
import { useSession } from '@/api/sessions';
import { useSessionItems, useMenu } from '@/api/pos';
import {
  useCheckout,
  useReprintInvoice,
  useMarkInvoicePrinted,
  printInvoicePdf,
} from '@/api/invoices';
import { useForceCloseUnprinted } from '@/api/sessions';
import { useAuthStore } from '@/store/authStore';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { PinConfirmModal } from '@/components/PinConfirmModal';
import { InvoicePanel } from './InvoicePanel';
import type { Invoice, InvoiceLineItem, PaymentMethod } from '@/types/invoice';
import {
  Banknote,
  CreditCard,
  Wallet,
  Package as PackageIcon,
  Loader2,
  CheckCircle,
  AlertCircle,
  Printer,
} from 'lucide-react';

interface CheckoutPanelProps {
  sessionId: string;
  onClose: () => void;
}

export function CheckoutPanel({ sessionId, onClose }: CheckoutPanelProps) {
  const [state, setState] = useState<'preview' | 'complete' | 'held'>('preview');
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [forceOpen, setForceOpen] = useState(false);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<PaymentMethod>('CASH');
  const [error, setError] = useState<string | null>(null);

  const token = useAuthStore((s) => s.accessToken);

  // Queries
  const sessionQuery = useSession(sessionId);
  const sessionItemsQuery = useSessionItems(sessionId);
  const menuQuery = useMenu();

  // Mutations
  const checkoutMutation = useCheckout();
  const requirePrintBeforeRelease = useFeatureFlagStore(
    (s) => s.flags.require_print_before_release,
  );
  const reprint = useReprintInvoice();
  const markPrinted = useMarkInvoicePrinted();
  const forceClose = useForceCloseUnprinted();

  // Combined status
  const isLoading = sessionQuery.isLoading || sessionItemsQuery.isLoading || menuQuery.isLoading;
  const isError = sessionQuery.isError || sessionItemsQuery.isError;

  const handleRetry = useCallback(() => {
    setError(null);
    sessionQuery.refetch();
    sessionItemsQuery.refetch();
    menuQuery.refetch();
  }, [sessionQuery, sessionItemsQuery, menuQuery]);

  // Helper to map menu item ID to name
  const getMenuItemName = useCallback(
    (itemId: string) => {
      const item = menuQuery.data?.find((i) => i.id === itemId);
      return item ? item.name : itemId;
    },
    [menuQuery.data]
  );

  // Calculations for PREVIEW state
  const { elapsedSeconds, previewInvoice } = useMemo(() => {
    const session = sessionQuery.data;
    const posItems = sessionItemsQuery.data ?? [];

    if (!session) {
      return {
        elapsedSeconds: 0,
        estimatedTimeCharge: 0,
        posTotalPaise: 0,
        previewInvoice: null,
      };
    }

    // Elapsed seconds (accurate calculation including pauses)
    let elapsed = 0;
    const start = new Date(session.started_at).getTime();
    if (session.paused_at) {
      const pausedTime = new Date(session.paused_at).getTime();
      elapsed = Math.max(0, Math.floor((pausedTime - start) / 1000) - session.total_paused_seconds);
    } else {
      elapsed = Math.max(0, Math.floor((Date.now() - start) / 1000) - session.total_paused_seconds);
    }

    // Client-side estimate for Time Charge (PER_MINUTE and FLAT_HOURLY)
    let estimatedCharge = 0;
    if (elapsed > 0) {
      const model = session.locked_pricing_model;
      const rate = session.locked_rate_paise;
      if (model === 'PER_MINUTE') {
        estimatedCharge = Math.ceil(elapsed / 60) * rate;
      } else if (model === 'FLAT_HOURLY') {
        estimatedCharge = Math.ceil(elapsed / 3600) * rate;
      }
    }

    // Calculate POS Total
    const posTotal = posItems.reduce((sum, item) => sum + item.unit_price_paise * item.quantity, 0);

    // Build line items for client-side preview
    const lineItems: InvoiceLineItem[] = [];

    // Add estimated time charge item
    if (estimatedCharge > 0) {
      lineItems.push({
        id: 'preview-time',
        invoice_id: 'preview',
        type: 'TIME_CHARGE',
        description: `Time Charge (${session.locked_pricing_model})`,
        quantity: session.locked_pricing_model === 'PER_MINUTE' ? Math.ceil(elapsed / 60) : Math.ceil(elapsed / 3600),
        unit_price_paise: session.locked_rate_paise,
        total_paise: estimatedCharge,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    }

    // Add POS items
    posItems.forEach((item) => {
      lineItems.push({
        id: item.id,
        invoice_id: 'preview',
        type: 'POS_ITEM',
        description: getMenuItemName(item.menu_item_id),
        quantity: item.quantity,
        unit_price_paise: item.unit_price_paise,
        total_paise: item.unit_price_paise * item.quantity,
        created_at: item.added_at,
        updated_at: item.added_at,
      });
    });

    // Add active discounts if any
    if (session.discount_paise > 0) {
      lineItems.push({
        id: 'preview-discount',
        invoice_id: 'preview',
        type: 'DISCOUNT',
        description: 'Session Discount',
        quantity: 1,
        unit_price_paise: session.discount_paise,
        total_paise: -session.discount_paise,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    }

    const totalPaise = Math.max(0, estimatedCharge + posTotal - session.discount_paise);

    const previewInvoiceObj: Invoice = {
      id: 'preview',
      session_id: session.id,
      member_id: session.member_id,
      shift_id: session.shift_id,
      time_charge_paise: estimatedCharge,
      package_credit_used_paise: 0, // Resolved at backend during checkout
      discount_paise: session.discount_paise,
      pos_total_paise: posTotal,
      total_paise: totalPaise,
      payment_method: selectedPaymentMethod,
      created_at: new Date().toISOString(),
      line_items: lineItems,
    };

    return {
      elapsedSeconds: elapsed,
      estimatedTimeCharge: estimatedCharge,
      posTotalPaise: posTotal,
      previewInvoice: previewInvoiceObj,
    };
  }, [sessionQuery.data, sessionItemsQuery.data, selectedPaymentMethod, getMenuItemName]);

  // Actions
  const handleConfirmCheckout = useCallback(() => {
    setError(null);
    checkoutMutation.mutate(
      { sessionId, paymentMethod: selectedPaymentMethod },
      {
        onSuccess: (invoice: Invoice) => {
          setInvoice(invoice);
          if (invoice.print_status === 'FAILED' && requirePrintBeforeRelease) {
            setState('held');
          } else {
            setState('complete');
          }
        },
        onError: (err: Error) => {
          setError(err.message || 'An error occurred during checkout.');
        },
      }
    );
  }, [checkoutMutation, sessionId, selectedPaymentMethod, requirePrintBeforeRelease]);

  const handlePrint = useCallback(async () => {
    if (!invoice) return;
    setError(null);
    try {
      await printInvoicePdf(invoice.id, token);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to open print page.';
      setError(message);
    }
  }, [invoice, token]);

  // Loading indicator
  if (isLoading) {
    return (
      <div className="flex h-full flex-col items-center justify-center space-y-4 py-8">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <p className="text-sm text-slate-400">Loading checkout breakdown...</p>
      </div>
    );
  }

  // Error fetching state
  if (isError || !sessionQuery.data) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-center p-6 space-y-4">
        <AlertCircle className="h-12 w-12 text-red-400" />
        <div>
          <h4 className="text-lg font-semibold text-slate-200">Failed to load session details</h4>
          <p className="text-sm text-slate-400 mt-1">
            Could not fetch session or billing status from server.
          </p>
        </div>
        <button
          type="button"
          onClick={handleRetry}
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors cursor-pointer"
        >
          Retry
        </button>
      </div>
    );
  }



  // Render HELD state (gate on, printer failed)
  if (state === 'held') {
    if (!invoice) return null;
    return (
      <div className="flex h-full flex-col space-y-5">
        <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
          <div className="p-2 rounded-full bg-amber-500/20 text-amber-400">
            <AlertCircle className="h-6 w-6" />
          </div>
          <div>
            <h4 className="text-base font-bold text-slate-100">Checkout held — printer issue</h4>
            <p className="text-xs text-slate-400 mt-0.5">
              The seat is still occupied. Reprint, or print the PDF and mark it printed,
              or force-close with your PIN.
            </p>
          </div>
        </div>

        <div className="flex gap-3 pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={async () => { await reprint.mutateAsync(invoice.id); setState('complete'); }}
            className="flex-1 py-3 px-4 rounded-xl border border-slate-700 bg-slate-800/50 hover:bg-slate-700 text-slate-200 font-medium transition-colors flex items-center justify-center gap-2 cursor-pointer"
          >
            <Printer className="h-5 w-5" /> Reprint
          </button>
          <button
            type="button"
            onClick={async () => {
              await printInvoicePdf(invoice.id, token);
              await markPrinted.mutateAsync(invoice.id);
              setState('complete');
            }}
            className="flex-1 py-3 px-4 rounded-xl border border-slate-700 bg-slate-800/50 hover:bg-slate-700 text-slate-200 font-medium transition-colors flex items-center justify-center gap-2 cursor-pointer"
          >
            <Printer className="h-5 w-5" /> PDF → Mark printed
          </button>
          <button
            type="button"
            onClick={() => setForceOpen(true)}
            className="flex-1 py-3 px-4 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold transition-colors flex items-center justify-center gap-2 cursor-pointer"
          >
            Force close (PIN)
          </button>
        </div>

        <PinConfirmModal
          open={forceOpen}
          title="Force close unprinted checkout"
          confirmLabel="Force close"
          isPending={forceClose.isPending}
          onClose={() => setForceOpen(false)}
          onConfirm={(pin, reason) => {
            forceClose.mutate(
              { sessionId: invoice.session_id, pin, reason },
              { onSuccess: () => { setForceOpen(false); setState('complete'); } },
            );
          }}
        />
      </div>
    );
  }


  // Render COMPLETE state
  if (state === 'complete') {
    if (!invoice) return null;

    return (
      <div className="flex h-full flex-col space-y-5">
        {/* Success header banner */}
        <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
          <div className="p-2 rounded-full bg-emerald-500/20 text-emerald-400">
            <CheckCircle className="h-6 w-6" />
          </div>
          <div>
            <h4 className="text-base font-bold text-slate-100">Session Checked Out Successfully</h4>
            <p className="text-xs text-slate-400 mt-0.5">
              Invoice #{invoice.id.substring(0, 8)} generated. Seat is now available.
            </p>
          </div>
        </div>

        {/* Invoice details */}
        <div className="flex-1 overflow-y-auto">
          <InvoicePanel invoice={invoice} sessionDurationSeconds={elapsedSeconds} />
        </div>

        {/* Action buttons */}
        <div className="flex gap-3 pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={handlePrint}
            className="flex-1 py-3 px-4 rounded-xl border border-slate-700 bg-slate-800/50 hover:bg-slate-700 text-slate-200 font-medium transition-colors flex items-center justify-center gap-2 cursor-pointer"
          >
            <Printer className="h-5 w-5" />
            Print Receipt
          </button>
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold transition-colors flex items-center justify-center gap-2 cursor-pointer"
          >
            New Session
          </button>
        </div>

        {/* Print error */}
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}
      </div>
    );
  }

  // Render PREVIEW state
  return (
    <div className="flex h-full flex-col space-y-5">
      {/* Preview invoice breakdown */}
      <div className="flex-1 overflow-y-auto pr-1">
        {previewInvoice && (
          <InvoicePanel invoice={previewInvoice} sessionDurationSeconds={elapsedSeconds} />
        )}

        {/* Payment method selector */}
        <div className="mt-6 space-y-3">
          <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider">
            Select Payment Method
          </label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { id: 'CASH', label: 'Cash', icon: Banknote, activeClass: 'border-emerald-500 bg-emerald-500/5 text-emerald-400' },
              { id: 'CARD', label: 'Card', icon: CreditCard, activeClass: 'border-blue-500 bg-blue-500/5 text-blue-400' },
              { id: 'WALLET', label: 'Wallet', icon: Wallet, activeClass: 'border-purple-500 bg-purple-500/5 text-purple-400' },
              { id: 'PACKAGE', label: 'Package', icon: PackageIcon, activeClass: 'border-amber-500 bg-amber-500/5 text-amber-400' },
            ].map((method) => {
              const Icon = method.icon;
              const isSelected = selectedPaymentMethod === method.id;
              return (
                <button
                  key={method.id}
                  type="button"
                  onClick={() => setSelectedPaymentMethod(method.id as PaymentMethod)}
                  className={`flex items-center gap-3 p-3 rounded-xl border transition-all text-left hover:bg-slate-800/40 cursor-pointer ${
                    isSelected
                      ? `${method.activeClass} border-2`
                      : 'border-slate-700 text-slate-300'
                  }`}
                >
                  <Icon className={`h-5 w-5 ${isSelected ? '' : 'text-slate-400'}`} />
                  <span className="text-sm font-medium">{method.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Mutation Error */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Checkout confirm action */}
      <div className="pt-4 border-t border-slate-800">
        <button
          type="button"
          onClick={handleConfirmCheckout}
          disabled={checkoutMutation.isPending}
          className="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-base transition-colors flex items-center justify-center gap-2 cursor-pointer"
        >
          {checkoutMutation.isPending ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Processing Payment...
            </>
          ) : (
            <>
              <CreditCard className="h-5 w-5" />
              Confirm Payment & Checkout
            </>
          )}
        </button>
      </div>
    </div>
  );
}
