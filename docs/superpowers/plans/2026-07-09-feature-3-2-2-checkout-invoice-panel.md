# Feature 3.2.2: Checkout and Invoice Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Checkout placeholder tab in `SessionDrawer` with a full checkout flow: invoice preview with time charge, package credit, POS items, discount, payment method selector, confirm payment, and receipt printing.

**Architecture:** A `CheckoutPanel` orchestrator is wired into `SessionDrawer`'s existing checkout tab slot. It follows the same React Query + props-down pattern as `POSPanel`. The component runs a two-state flow: **PREVIEW** (fetch session + POS items → show breakdown + payment selector → confirm) → **COMPLETE** (show server-returned invoice → print receipt). New `api/sessions.ts` fetches session detail; `api/checkout.ts` sends the checkout mutation.

**Tech Stack:** React 18, TypeScript 5, TailwindCSS 4, TanStack React Query 5, Zustand 5, Lucide React, Vitest + @testing-library/react

## Global Constraints

- All monetary values are integer **paise** in data layer; `formatPaise(paise): "Rs. X.XX"` is the single display conversion (NFR-DATA-002)
- Payment methods: `CASH`, `CARD`, `WALLET`, `PACKAGE` (matching backend `PaymentMethod` enum)
- Invoice line item types: `TIME_CHARGE`, `POS_ITEM`, `DISCOUNT`, `PACKAGE_CREDIT`
- Checkout endpoint: `POST /api/sessions/{id}/checkout` body is `{payment_method: PaymentMethod}`; returns `InvoiceResponse`
- Session detail: `GET /api/sessions/{id}` returns `SessionResponse` with `locked_rate_paise`, `locked_pricing_model`, `started_at`, `paused_at`, `total_paused_seconds`
- POS items: `GET /api/pos/items/{sessionId}` returns `SessionPOSItem[]` (already implemented)
- Invoice detail: `GET /api/invoices/{id}` returns `InvoiceResponse` with `line_items` array
- Receipt PDF: `GET /api/invoices/{id}/pdf` returns HTML that triggers `window.print()`
- Checkout marks session `COMPLETED`, seat `AVAILABLE`; `SHOW_OVERLAY` sent to agent; receipt printed async (backend handles this — frontend just calls the endpoint)
- All components follow existing design system: dark slate theme, `slate-900` backgrounds, `text-emerald-400` for money, blue accents for actions
- Match existing POS panel patterns: React Query hooks in `api/`, orchestrator passes `data/isLoading/isError/onRetry` to sub-components

---

## File Structure Overview

```
frontend/src/
├── api/
│   ├── sessions.ts         # NEW: Session detail fetch + checkout mutation
│   └── invoices.ts         # NEW: Invoice detail fetch + PDF print helper
├── components/
│   ├── InvoicePanel.tsx    # NEW: Invoice breakdown display (read-only)
│   ├── CheckoutPanel.tsx   # NEW: Main orchestrator (PREVIEW ↔ COMPLETE states)
│   └── pos/
│       ├── MenuGrid.tsx
│       ├── SessionTab.tsx
│       ├── MenuItemCard.ts
│       └── ...
├── hooks/
│   └── useFormatPaise.ts   # EXISTING: Currency formatting
└── types/
    ├── invoice.ts          # NEW: Invoice types mirroring backend schemas
    └── pos.ts              # EXISTING: MenuItem, SessionPOSItem
```

---

## Task Breakdown

### Task 1: Create Invoice Types (`frontend/src/types/invoice.ts`)

**Files:** Create `frontend/src/types/invoice.ts`
**Interfaces:** None (new file)
**Produces:** Type definitions matching backend `InvoiceResponse` and `InvoiceLineItemResponse`

```typescript
// frontend/src/types/invoice.ts
/** Invoice line item as returned by backend */
export interface InvoiceLineItem {
  id: string;
  invoice_id: string;
  type: 'TIME_CHARGE' | 'POS_ITEM' | 'DISCOUNT' | 'PACKAGE_CREDIT';
  description: string;
  quantity: number;
  unit_price_paise: number;
  total_paise: number;
}

/** Full invoice response from GET /api/invoices/{id} or POST /api/sessions/{id}/checkout */
export interface InvoiceResponse {
  id: string;
  session_id: string;
  member_id: string | null;
  shift_id: string | null;
  time_charge_paise: number;
  package_credit_used_paise: number;
  discount_paise: number;
  pos_total_paise: number;
  total_paise: number;
  payment_method: 'CASH' | 'CARD' | 'WALLET' | 'PACKAGE';
  created_at: string; // ISO datetime
  line_items: InvoiceLineItem[];
}

/** Request body for checkout mutation */
export interface CheckoutRequest {
  payment_method: 'CASH' | 'CARD' | 'WALLET' | 'PACKAGE';
}
```

---

### Task 2: Create Session API Hooks (`frontend/src/api/sessions.ts`)

**Files:** Create `frontend/src/api/sessions.ts`
**Consumes:** `useAuthStore` from `@/store/authStore`
**Produces:** `useSession` hook, `useCheckoutSession` mutation

```typescript
// frontend/src/api/sessions.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import type { SessionResponse } from '@/types/session'; // Need to create this from session.ts types
import type { InvoiceResponse, CheckoutRequest } from '@/types/invoice';

const API_BASE = '/api';

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------
function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

// ----------------------------------------------------------------------------
// Fetch functions
// ----------------------------------------------------------------------------
/** Fetch session detail for checkout preview. */
export async function fetchSession(
  sessionId: string,
  token: string | null
): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch session: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as SessionResponse;
}

/** Checkout session and generate invoice. */
export async function checkoutSession(
  sessionId: string,
  body: CheckoutRequest,
  token: string | null
): Promise<InvoiceResponse> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/checkout`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to checkout' }));
    throw new Error(err.detail ?? `Checkout failed: ${res.status}`);
  }
  return (await res.json()) as InvoiceResponse;
}

/** Fetch invoice detail for print/preview. */
export async function fetchInvoice(
  invoiceId: string,
  token: string | null
): Promise<InvoiceResponse> {
  const res = await fetch(`${API_BASE}/invoices/${invoiceId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch invoice: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as InvoiceResponse;
}

// ----------------------------------------------------------------------------
// React Query hooks
// ----------------------------------------------------------------------------
/** Hook to fetch session detail for checkout. */
export function useSession(sessionId: string) {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => fetchSession(sessionId, token),
    enabled: !!sessionId,
    refetchOnWindowFocus: false,
  });
}

/** Mutation hook to checkout a session. */
export function useCheckoutSession() {
  const token = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, body }: { sessionId: string; body: CheckoutRequest }) =>
      checkoutSession(sessionId, body, token),
    onSuccess: (invoice, variables) => {
      // Invalidate session list and seat grid
      queryClient.invalidateQueries({ queryKey: ['sessions', 'active'] });
      queryClient.invalidateQueries({ queryKey: ['seats'] });
      // Cache the generated invoice for the COMPLETE state
      queryClient.setQueryData(['invoice', invoice.id], invoice);
    },
  });
}

/** Hook to fetch invoice detail (for print/preview in COMPLETE state). */
export function useInvoice(invoiceId: string) {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: () => fetchInvoice(invoiceId, token),
    enabled: !!invoiceId,
    refetchOnWindowFocus: false,
  });
}

/** Helper to open PDF receipt in new tab for printing. */
export async function printInvoicePdf(invoiceId: string, token: string | null): Promise<void> {
  const res = await fetch(`${API_BASE}/invoices/${invoiceId}/pdf`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch PDF: ${res.status} ${res.statusText}`);
  }
  // Open in new tab which triggers window.print() via inline script
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const win = window.open(url, '_blank');
  if (!win) {
    throw new Error('Popup blocked - please allow popups for receipt printing');
  }
}
```

---

### Task 3: Create Session Types (`frontend/src/types/session.ts`)

**Files:** Create `frontend/src/types/session.ts`
**Consumes:** None
**Produces:** `SessionResponse` type matching backend schema

```typescript
// frontend/src/types/session.ts
/** Pricing model from backend */
export enum PricingModel {
  PER_MINUTE = 'PER_MINUTE',
  FLAT_HOURLY = 'FLAT_HOURLY',
  TIME_BLOCK = 'TIME_BLOCK',
}

/** Session status from backend */
export enum SessionStatus {
  ACTIVE = 'ACTIVE',
  PAUSED = 'PAUSED',
  COMPLETED = 'COMPLETED',
  ABANDONED = 'ABANDONED',
}

/** Session response from GET /api/sessions/{id} */
export interface SessionResponse {
  id: string;
  seat_id: string;
  member_id: string | null;
  shift_id: string | null;
  status: SessionStatus;
  started_at: string; // ISO datetime
  ended_at: string | null;
  paused_at: string | null;
  total_paused_seconds: number;
  locked_rate_paise: number;
  locked_pricing_model: PricingModel;
  package_entitlement_id: string | null;
  promotion_id: string | null;
  discount_paise: number;
  payment_method: 'CASH' | 'CARD' | 'WALLET' | 'PACKAGE' | null;
  created_at: string;
  updated_at: string;
}
```

---

### Task 4: Create Invoice Panel Component (`frontend/src/components/InvoicePanel.tsx`)

**Files:** Create `frontend/src/components/InvoicePanel.tsx`
**Consumes:** `formatPaise` from `@/hooks/useFormatPaise`, `InvoiceResponse` from `@/types/invoice`
**Produces:** Read-only invoice breakdown display component

```tsx
// frontend/src/components/InvoicePanel.tsx
import { formatPaise } from '@/hooks/useFormatPaise';
import type { InvoiceResponse } from '@/types/invoice';
import { CreditCard, Package, Tag, Clock, Minus, Plus } from 'lucide-react';

interface InvoicePanelProps {
  invoice: InvoiceResponse;
  sessionDurationSeconds?: number; // For displaying formatted duration
}

/** Read-only invoice breakdown display.
 *  Shows: time charge, package credit, discounts, POS items, total, payment method. */
export function InvoicePanel({ invoice, sessionDurationSeconds }: InvoicePanelProps) {
  const formatDuration = (seconds: number): string => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return h > 0 ? `${h}h ${m}m ${s}s` : `${m}m ${s}s`;
  };

  return (
    <div className="space-y-4">
      {/* Header with session duration */}
      {sessionDurationSeconds !== undefined && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700">
          <span className="text-sm text-slate-300">Session Duration</span>
          <span className="font-mono text-lg font-semibold text-white">
            {formatDuration(sessionDurationSeconds)}
          </span>
        </div>
      )}

      {/* Time Charge */}
      {invoice.time_charge_paise > 0 && (
        <InvoiceRow
          icon={<Clock className="h-4 w-4 text-blue-400" />}
          label="Time Charge"
          value={formatPaise(invoice.time_charge_paise)}
          description={invoice.locked_pricing_model ? `Rate locked at session start (${invoice.locked_pricing_model})` : undefined}
        />
      )}

      {/* Package Credit Used */}
      {invoice.package_credit_used_paise > 0 && (
        <InvoiceRow
          icon={<Package className="h-4 w-4 text-emerald-400" />}
          label="Package Credit"
          value={formatPaise(invoice.package_credit_used_paise)}
          isCredit
          description="Deducted from active time package"
        />
      )}

      {/* Discounts */}
      {invoice.discount_paise > 0 && (
        <InvoiceRow
          icon={<Tag className="h-4 w-4 text-amber-400" />}
          label="Discount"
          value={formatPaise(invoice.discount_paise)}
          isCredit
          description={getDiscountDescription(invoice)}
        />
      )}

      {/* POS Items */}
      {invoice.line_items
        .filter((li) => li.type === 'POS_ITEM')
        .map((item) => (
          <InvoiceRow
            key={item.id}
            icon={<Plus className="h-4 w-4 text-slate-400" />}
            label={item.description}
            value={formatPaise(item.total_paise)}
            description={`Qty: ${item.quantity} × ${formatPaise(item.unit_price_paise)}`}
          />
        ))}

      {/* Divider before total */}
      <div className="border-t border-slate-700 my-2" />

      {/* Total */}
      <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700">
        <span className="text-base font-semibold text-white">Total</span>
        <span className="font-mono text-xl font-bold text-emerald-400">
          {formatPaise(invoice.total_paise)}
        </span>
      </div>

      {/* Payment Method */}
      <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700">
        <span className="text-sm text-slate-300">Payment Method</span>
        <PaymentMethodBadge method={invoice.payment_method} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface InvoiceRowProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  isCredit?: boolean;
  description?: string;
}

function InvoiceRow({ icon, label, value, isCredit, description }: InvoiceRowProps) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/30 border border-slate-700/50">
      <div className="flex-shrink-0 mt-0.5 text-slate-500">{icon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-medium text-slate-200">{label}</span>
          <span className={`font-mono text-sm ${isCredit ? 'text-emerald-400' : 'text-white'}`}>
            {isCredit ? '-' : ''}{value}
          </span>
        </div>
        {description && (
          <p className="mt-1 text-xs text-slate-500 truncate">{description}</p>
        )}
      </div>
    </div>
  );
}

interface PaymentMethodBadgeProps {
  method: 'CASH' | 'CARD' | 'WALLET' | 'PACKAGE';
}

function PaymentMethodBadge({ method }: PaymentMethodBadgeProps) {
  const config = {
    CASH: { label: 'Cash', icon: '💵', color: 'text-green-400 bg-green-400/10 border-green-400/20' },
    CARD: { label: 'Card', icon: '💳', color: 'text-blue-400 bg-blue-400/10 border-blue-400/20' },
    WALLET: { label: 'Wallet', icon: '👛', color: 'text-purple-400 bg-purple-400/10 border-purple-400/20' },
    PACKAGE: { label: 'Package', icon: '📦', color: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' },
  }[method];

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium border ${config.color}`}>
      <span>{config.icon}</span>
      {config.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getDiscountDescription(invoice: InvoiceResponse): string {
  const parts: string[] = [];
  if (invoice.promotion_id) parts.push('Promotion applied');
  if (invoice.member_id && invoice.discount_paise > 0) parts.push('Member loyalty discount');
  if (invoice.package_entitlement_id) parts.push('Package rate applied');
  return parts.join(' • ') || 'Discount applied';
}
```

---

### Task 5: Create Checkout Panel Component (`frontend/src/components/CheckoutPanel.tsx`)

**Files:** Create `frontend/src/components/CheckoutPanel.tsx`
**Consumes:** `useSession`, `useCheckoutSession`, `useSessionItems` from `@/api/sessions`, `formatPaise` from `@/hooks/useFormatPaise`, `InvoicePanel`
**Produces:** Main orchestrator component with PREVIEW/COMPLETE states

```tsx
// frontend/src/components/CheckoutPanel.tsx
import { useState, useCallback } from 'react';
import { useSession, useCheckoutSession, useSessionItems } from '@/api/sessions';
import { formatPaise } from '@/hooks/useFormatPaise';
import { InvoicePanel } from './InvoicePanel';
import { CreditCard, Loader2, CheckCircle, AlertCircle, Printer } from 'lucide-react';

interface CheckoutPanelProps {
  sessionId: string;
}

export function CheckoutPanel({ sessionId }: CheckoutPanelProps) {
  const [state, setState] = useState<'preview' | 'complete'>('preview');
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState<
    'CASH' | 'CARD' | 'WALLET' | 'PACKAGE'
  >('CASH');
  const [error, setError] = useState<string | null>(null);

  // Fetch session detail for preview
  const sessionQuery = useSession(sessionId);
  // Fetch POS items for preview
  const sessionItemsQuery = useSessionItems(sessionId);

  // Checkout mutation
  const checkoutMutation = useCheckoutSession();

  // Combined loading state
  const isLoading = sessionQuery.isLoading || sessionItemsQuery.isLoading;
  const isError = sessionQuery.isError || sessionItemsQuery.isError;
  const retry = () => {
    sessionQuery.refetch();
    sessionItemsQuery.refetch();
  };

  // Calculate elapsed seconds for display
  const elapsedSeconds = sessionQuery.data
    ? Math.floor((Date.now() - new Date(sessionQuery.data.started_at).getTime()) / 1000) -
      sessionQuery.data.total_paused_seconds
    : 0;

  const handleCheckout = useCallback(() => {
    setError(null);
    checkoutMutation.mutate(
      { sessionId, body: { payment_method: selectedPaymentMethod } },
      {
        onSuccess: (invoice) => {
          setState('complete');
        },
        onError: (err: Error) => {
          setError(err.message);
        },
      }
    );
  }, [checkoutMutation, selectedPaymentMethod, sessionId]);

  const handlePrint = useCallback(async () => {
    // In COMPLETE state, we have the invoice from mutation
    // Could also use the print endpoint directly
    window.print();
  }, []);

  const handleNewSession = useCallback(() => {
    // Reset to initial state - parent SessionDrawer will close
    setState('preview');
    setSelectedPaymentMethod('CASH');
    setError(null);
  }, []);

  // -------------------------------------------------------------------------
  // PREVIEW STATE
  // -------------------------------------------------------------------------
  if (state === 'preview') {
    if (isLoading) {
      return <CheckoutSkeleton />;
    }

    if (isError) {
      return (
        <ErrorState
          message="Failed to load checkout data"
          onRetry={retry}
        />
      );
    }

    const session = sessionQuery.data;
    const posItems = sessionItemsQuery.data ?? [];

    if (!session) {
      return <EmptyState message="Session not found" />;
    }

    // Calculate POS total
    const posTotalPaise = posItems.reduce(
      (sum, item) => sum + item.unit_price_paise * item.quantity,
      0
    );

    return (
      <div className="flex h-full flex-col">
        {/* Preview header */}
        <div className="mb-4 p-3 rounded-lg bg-slate-800/50 border border-slate-700">
          <h3 className="text-sm font-semibold text-slate-200">Invoice Preview</h3>
          <p className="text-xs text-slate-400 mt-1">
            Review the breakdown and select payment method
          </p>
        </div>

        {/* Invoice breakdown */}
        <InvoicePanel
          invoice={{
            id: 'preview',
            session_id: session.id,
            member_id: session.member_id,
            shift_id: session.shift_id,
            time_charge_paise: 0, // Will be calculated by backend on checkout
            package_credit_used_paise: 0,
            discount_paise: session.discount_paise,
            pos_total_paise: posTotalPaise,
            total_paise: posTotalPaise, // Time charge added by backend
            payment_method: selectedPaymentMethod,
            created_at: new Date().toISOString(),
            line_items: [
              ...(session.locked_rate_paise > 0
                ? [{
                    id: 'time-charge',
                    invoice_id: 'preview',
                    type: 'TIME_CHARGE' as const,
                    description: `Time charge (${session.locked_pricing_model})`,
                    quantity: 1,
                    unit_price_paise: 0, // Backend calculates
                    total_paise: 0,
                  }]
                : []),
              ...posItems.map((item, idx) => ({
                id: `pos-${idx}`,
                invoice_id: 'preview',
                type: 'POS_ITEM' as const,
                description: `${item.menu_item_id} × ${item.quantity}`, // Will be enriched below
                quantity: item.quantity,
                unit_price_paise: item.unit_price_paise,
                total_paise: item.unit_price_paise * item.quantity,
              })),
              ...(session.discount_paise > 0
                ? [{
                    id: 'discount',
                    invoice_id: 'preview',
                    type: 'DISCOUNT' as const,
                    description: 'Discount applied',
                    quantity: 1,
                    unit_price_paise: session.discount_paise,
                    total_paise: session.discount_paise,
                  }]
                : []),
            ],
          }}
          sessionDurationSeconds={elapsedSeconds}
        />

        {/* Payment method selector */}
        <div className="mt-6 space-y-3">
          <label className="block text-sm font-medium text-slate-300">Payment Method</label>
          <div className="grid grid-cols-2 gap-3">
            {(['CASH', 'CARD', 'WALLET', 'PACKAGE'] as const).map((method) => (
              <button
                key={method}
                type="button"
                onClick={() => setSelectedPaymentMethod(method)}
                className={`relative flex flex-col items-center justify-center gap-2 p-4 rounded-xl border-2 transition-all ${
                  selectedPaymentMethod === method
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-slate-700 hover:border-slate-600 hover:bg-slate-800/50'
                }`}
              >
                <PaymentMethodIcon method={method} size={24} />
                <span className="text-sm font-medium text-slate-100">
                  {method === 'WALLET' ? 'Wallet' : method}
                </span>
                {selectedPaymentMethod === method && (
                  <div className="absolute top-2 right-2 h-5 w-5 rounded-full bg-blue-500 flex items-center justify-center">
                    <CheckCircle className="h-3 w-3 text-white" />
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Error display */}
        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-900/30 border border-red-800/50 text-red-200 text-sm flex items-center gap-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Confirm button */}
        <button
          type="button"
          onClick={handleCheckout}
          disabled={checkoutMutation.isPending}
          className="mt-6 w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-base transition-colors flex items-center justify-center gap-2"
        >
          {checkoutMutation.isPending ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              <CreditCard className="h-5 w-5" />
              Confirm Payment
            </>
          )}
        </button>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // COMPLETE STATE
  // -------------------------------------------------------------------------
  const invoice = checkoutMutation.data;
  if (!invoice) {
    return <EmptyState message="Invoice not available" />;
  }

  return (
    <div className="flex h-full flex-col">
      {/* Success header */}
      <div className="mb-4 p-3 rounded-lg bg-emerald-900/30 border border-emerald-800/50 flex items-center gap-3">
        <div className="p-2 rounded-full bg-emerald-500/20">
          <CheckCircle className="h-6 w-6 text-emerald-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-emerald-300">Payment Complete</h3>
          <p className="text-sm text-emerald-500">Invoice #{invoice.id.slice(0, 8)} generated</p>
        </div>
      </div>

      {/* Invoice display */}
      <InvoicePanel
        invoice={invoice}
        sessionDurationSeconds={elapsedSeconds}
      />

      {/* Action buttons */}
      <div className="mt-6 flex gap-3">
        <button
          type="button"
          onClick={handlePrint}
          className="flex-1 py-3 px-4 rounded-xl border border-slate-600 bg-slate-800 hover:bg-slate-700 text-slate-100 font-medium transition-colors flex items-center justify-center gap-2"
        >
          <Printer className="h-5 w-5" />
          Print Receipt
        </button>
        <button
          type="button"
          onClick={handleNewSession}
          className="flex-1 py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-medium transition-colors flex items-center justify-center gap-2"
        >
          New Session
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CheckoutSkeleton() {
  return (
    <div className="flex h-full flex-col space-y-4">
      <div className="h-10 w-3/4 animate-pulse rounded-lg bg-slate-800" />
      <div className="h-32 w-full animate-pulse rounded-lg bg-slate-800" />
      <div className="h-24 w-full animate-pulse rounded-lg bg-slate-800" />
      <div className="grid grid-cols-2 gap-3">
        <div className="h-24 animate-pulse rounded-xl bg-slate-800" />
        <div className="h-24 animate-pulse rounded-xl bg-slate-800" />
      </div>
      <div className="h-12 w-full animate-pulse rounded-xl bg-slate-800" />
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center p-6">
      <AlertCircle className="h-12 w-12 text-red-400 mb-4" />
      <h3 className="text-lg font-semibold text-slate-200 mb-2">{message}</h3>
      <p className="text-sm text-slate-400 mb-4">Please try again or contact support</p>
      <button
        type="button"
        onClick={onRetry}
        className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium"
      >
        Retry
      </button>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center p-6">
      <CreditCard className="h-12 w-12 text-slate-500 mb-4" />
      <h3 className="text-lg font-semibold text-slate-300 mb-2">{message}</h3>
      <p className="text-sm text-slate-500">No invoice data available</p>
    </div>
  );
}

interface PaymentMethodIconProps {
  method: 'CASH' | 'CARD' | 'WALLET' | 'PACKAGE';
  size?: number;
}

function PaymentMethodIcon({ method, size = 24 }: PaymentMethodIconProps) {
  const icons = {
    CASH: '💵',
    CARD: '💳',
    WALLET: '👛',
    PACKAGE: '📦',
  };
  return <span style={{ fontSize: size }}>{icons[method]}</span>;
}
```

---

### Task 6: Update Session Drawer (`frontend/src/components/SessionDrawer.tsx`)

**Files:** Modify `frontend/src/components/SessionDrawer.tsx`
**Consumes:** `CheckoutPanel` from `@/components/CheckoutPanel`
**Produces:** Updated drawer with functional checkout tab

```tsx
// frontend/src/components/SessionDrawer.tsx
import { useEffect, useState, useCallback } from 'react';
import type { Seat } from '@/types/seat';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { POSPanel } from './pos/POSPanel';
import { CheckoutPanel } from './CheckoutPanel'; // NEW IMPORT
import { X, ShoppingCart, CreditCard, Terminal } from 'lucide-react';

type DrawerTab = 'pos' | 'checkout' | 'commands';

interface SessionDrawerProps {
  seat: Seat;
  sessionId: string;
  onClose: () => void;
}

/** Slide-out drawer for IN_USE seats — contains POS, Checkout, and Commands tabs. */
export function SessionDrawer({ seat, sessionId, onClose }: SessionDrawerProps) {
  const posEnabled = useFeatureFlagStore((s) => s.flags.enable_pos);
  const [activeTab, setActiveTab] = useState<DrawerTab>(posEnabled ? 'pos' : 'checkout');
  const [isOpen, setIsOpen] = useState(false);

  // Animate open on mount
  useEffect(() => {
    const timer = setTimeout(() => setIsOpen(true), 10);
    return () => clearTimeout(timer);
  }, []);

  // Close with animation
  const handleClose = useCallback(() => {
    setIsOpen(false);
    setTimeout(onClose, 300);
  }, [onClose]);

  // Escape key handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleClose]);

  // Available tabs (POS only if enabled)
  const tabs: { id: DrawerTab; label: string; icon: React.ReactNode }[] = [
    ...(posEnabled
      ? [{ id: 'pos' as DrawerTab, label: 'POS', icon: <ShoppingCart className="h-4 w-4" /> }]
      : []),
    { id: 'checkout', label: 'Checkout', icon: <CreditCard className="h-4 w-4" /> },
    { id: 'commands', label: 'Commands', icon: <Terminal className="h-4 w-4" /> },
  ];

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity duration-300 ${
          isOpen ? 'opacity-100' : 'opacity-0'
        }`}
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        className={`fixed right-0 top-0 z-50 flex h-full w-full max-w-2xl flex-col border-l border-slate-700 bg-slate-900 shadow-2xl transition-transform duration-300 ease-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        {/* Header */}
        <header className="flex items-center justify-between border-b border-slate-700 bg-slate-800 px-5 py-4">
          <div>
            <h2 id="drawer-title" className="text-lg font-bold text-white">
              {seat.name}
            </h2>
            <p className="text-xs text-slate-400">
              Session active · {seat.is_console ? 'Console' : 'PC'}
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-700 hover:text-white"
            aria-label="Close drawer"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        {/* Tab switcher */}
        <nav className="flex border-b border-slate-700 bg-slate-800/50 px-5" aria-label="Drawer tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-slate-400 hover:border-slate-600 hover:text-slate-200'
              }`}
              aria-selected={activeTab === tab.id}
              role="tab"
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Tab content */}
        <div className="flex-1 overflow-hidden p-5">
          {activeTab === 'pos' && posEnabled && (
            <POSPanel sessionId={sessionId} />
          )}
          {activeTab === 'checkout' && (
            <CheckoutPanel sessionId={sessionId} />
          )}
          {activeTab === 'commands' && (
            <PlaceholderTab
              icon={<Terminal className="h-8 w-8" />}
              title="Commands"
              description="Remote commands and seat controls coming in a future update"
            />
          )}
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Placeholder tab content (unchanged)
// ---------------------------------------------------------------------------

function PlaceholderTab({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <div className="mb-4 rounded-2xl bg-slate-800 p-5 text-slate-500">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-slate-300">{title}</h3>
      <p className="mt-2 max-w-xs text-sm text-slate-500">{description}</p>
    </div>
  );
}
```

---

### Task 7: Create Invoice API Hooks (`frontend/src/api/invoices.ts`)

**Files:** Create `frontend/src/api/invoices.ts`
**Consumes:** `useAuthStore` from `@/store/authStore`
**Produces:** `useInvoice` hook, `printInvoicePdf` helper

```typescript
// frontend/src/api/invoices.ts
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';
import type { InvoiceResponse } from '@/types/invoice';

const API_BASE = '/api';

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export async function fetchInvoice(
  invoiceId: string,
  token: string | null
): Promise<InvoiceResponse> {
  const res = await fetch(`${API_BASE}/invoices/${invoiceId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch invoice: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as InvoiceResponse;
}

/** Hook to fetch invoice detail. */
export function useInvoice(invoiceId: string) {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: () => fetchInvoice(invoiceId, token),
    enabled: !!invoiceId,
    refetchOnWindowFocus: false,
  });
}

/** Open PDF receipt in new tab for printing. */
export async function printInvoicePdf(invoiceId: string, token: string | null): Promise<void> {
  const res = await fetch(`${API_BASE}/invoices/${invoiceId}/pdf`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch PDF: ${res.status} ${res.statusText}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const win = window.open(url, '_blank');
  if (!win) {
    throw new Error('Popup blocked - please allow popups for receipt printing');
  }
}
```

---

### Task 8: Write Unit Tests

**Files:**
- Create `frontend/src/components/InvoicePanel.test.tsx`
- Create `frontend/src/components/CheckoutPanel.test.tsx`
- Create `frontend/src/api/sessions.test.ts`

**Tests for InvoicePanel:**
```tsx
// frontend/src/components/InvoicePanel.test.tsx
import { render, screen } from '@testing-library/react';
import { InvoicePanel } from './InvoicePanel';
import type { InvoiceResponse } from '@/types/invoice';

const mockInvoice: InvoiceResponse = {
  id: 'inv-001',
  session_id: 'sess-001',
  member_id: 'mem-001',
  shift_id: 'shift-001',
  time_charge_paise: 30000, // Rs. 300.00
  package_credit_used_paise: 15000, // Rs. 150.00
  discount_paise: 3000, // Rs. 30.00
  pos_total_paise: 25000, // Rs. 250.00
  total_paise: 37000, // Rs. 370.00
  payment_method: 'CASH',
  created_at: '2026-07-09T10:00:00Z',
  line_items: [
    { id: 'li-1', invoice_id: 'inv-001', type: 'TIME_CHARGE', description: 'Time charge (PER_MINUTE)', quantity: 1, unit_price_paise: 30000, total_paise: 30000 },
    { id: 'li-2', invoice_id: 'inv-001', type: 'PACKAGE_CREDIT', description: 'Package credit', quantity: 1, unit_price_paise: 15000, total_paise: 15000 },
    { id: 'li-3', invoice_id: 'inv-001', type: 'DISCOUNT', description: 'Member loyalty discount', quantity: 1, unit_price_paise: 3000, total_paise: 3000 },
    { id: 'li-4', invoice_id: 'inv-001', type: 'POS_ITEM', description: 'Coke × 2', quantity: 2, unit_price_paise: 12500, total_paise: 25000 },
  ],
};

describe('InvoicePanel', () => {
  it('renders time charge, package credit, discount, POS items, and total', () => {
    render(<InvoicePanel invoice={mockInvoice} sessionDurationSeconds={7200} />);

    expect(screen.getByText('Session Duration')).toBeVisible();
    expect(screen.getByText('2h 0m 0s')).toBeVisible(); // 7200s = 2h
    expect(screen.getByText('Time Charge')).toBeVisible();
    expect(screen.getByText('Rs. 300.00')).toBeVisible();
    expect(screen.getByText('Package Credit')).toBeVisible();
    expect(screen.getByText('Rs. 150.00')).toBeVisible();
    expect(screen.getByText('Discount')).toBeVisible();
    expect(screen.getByText('Rs. 30.00')).toBeVisible();
    expect(screen.getByText('Coke × 2')).toBeVisible();
    expect(screen.getByText('Total')).toBeVisible();
    expect(screen.getByText('Rs. 370.00')).toBeVisible();
    expect(screen.getByText('Cash')).toBeVisible();
  });

  it('hides package credit row when zero', () => {
    const invoiceNoPackage = { ...mockInvoice, package_credit_used_paise: 0 };
    render(<InvoicePanel invoice={invoiceNoPackage} />);
    expect(screen.queryByText('Package Credit')).not.toBeInTheDocument();
  });

  it('hides discount row when zero', () => {
    const invoiceNoDiscount = { ...mockInvoice, discount_paise: 0 };
    render(<InvoicePanel invoice={invoiceNoDiscount} />);
    expect(screen.queryByText('Discount')).not toBeInTheDocument();
  });

  it('displays different payment method badges correctly', () => {
    const { rerender } = render(<InvoicePanel invoice={mockInvoice} />);
    expect(screen.getByText('Cash')).toBeVisible();

    rerender(<InvoicePanel invoice={{ ...mockInvoice, payment_method: 'CARD' }} />);
    expect(screen.getByText('Card')).toBeVisible();

    rerender(<InvoicePanel invoice={{ ...mockInvoice, payment_method: 'WALLET' }} />);
    expect(screen.getByText('Wallet')).toBeVisible();

    rerender(<InvoicePanel invoice={{ ...mockInvoice, payment_method: 'PACKAGE' }} />);
    expect(screen.getByText('Package')).toBeVisible();
  });
});
```

**Tests for CheckoutPanel:**
```tsx
// frontend/src/components/CheckoutPanel.test.tsx
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CheckoutPanel } from './CheckoutPanel';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';

// Mock hooks
jest.mock('@/api/sessions', () => ({
  useSession: jest.fn(),
  useCheckoutSession: jest.fn(),
  useSessionItems: jest.fn(),
}));

jest.mock('@/hooks/useFormatPaise', () => ({
  formatPaise: (paise: number) => `Rs. ${(paise / 100).toFixed(2)}`,
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({ accessToken: 'test-token' }),
}));

import { useSession, useCheckoutSession, useSessionItems } from '@/api/sessions';

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockSession = {
  id: 'sess-001',
  seat_id: 'seat-001',
  member_id: 'mem-001',
  shift_id: 'shift-001',
  status: 'ACTIVE',
  started_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
  ended_at: null,
  paused_at: null,
  total_paused_seconds: 0,
  locked_rate_paise: 5000,
  locked_pricing_model: 'PER_MINUTE',
  package_entitlement_id: null,
  promotion_id: null,
  discount_paise: 0,
  payment_method: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockPosItems = [
  { id: 'pos-1', session_id: 'sess-001', menu_item_id: 'item-1', quantity: 2, unit_price_paise: 12500, added_at: new Date().toISOString() },
];

const mockInvoice = {
  id: 'inv-001',
  session_id: 'sess-001',
  member_id: 'mem-001',
  shift_id: 'shift-001',
  time_charge_paise: 30000,
  package_credit_used_paise: 0,
  discount_paise: 0,
  pos_total_paise: 25000,
  total_paise: 55000,
  payment_method: 'CASH',
  created_at: new Date().toISOString(),
  line_items: [],
};

describe('CheckoutPanel', () => {
  const mockMutate = jest.fn();
  const mockMutateAsync = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (useSession as jest.Mock).mockReturnValue({
      data: mockSession,
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });
    (useSessionItems as jest.Mock).mockReturnValue({
      data: mockPosItems,
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });
    (useCheckoutSession as jest.Mock).mockReturnValue({
      mutate: mockMutate,
      mutateAsync: mockMutateAsync,
      isPending: false,
      data: mockInvoice,
      isError: false,
      error: null,
    });
  });

  it('renders preview state with session duration and POS items', () => {
    render(<CheckoutPanel sessionId="sess-001" />, { wrapper: createWrapper() });

    expect(screen.getByText('Invoice Preview')).toBeVisible();
    expect(screen.getByText('Session Duration')).toBeVisible();
    expect(screen.getByText('Time Charge')).toBeVisible();
    expect(screen.getByText('POS_ITEM')).toBeVisible();
    expect(screen.getByText('Confirm Payment')).toBeVisible();
  });

  it('shows payment method selector with all 4 options', () => {
    render(<CheckoutPanel sessionId="sess-001" />, { wrapper: createWrapper() });

    expect(screen.getByText('Cash')).toBeVisible();
    expect(screen.getByText('Card')).toBeVisible();
    expect(screen.getByText('Wallet')).toBeVisible();
    expect(screen.getByText('Package')).toBeVisible();
  });

  it('calls checkout mutation on confirm with selected payment method', async () => {
    const user = userEvent.setup();
    render(<CheckoutPanel sessionId="sess-001" />, { wrapper: createWrapper() });

    // Select CARD
    await user.click(screen.getByText('Card'));

    // Click confirm
    await user.click(screen.getByText('Confirm Payment'));

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(
        { sessionId: 'sess-001', body: { payment_method: 'CARD' } },
        expect.any(Object)
      );
    });
  });

  it('shows loading state during checkout', async () => {
    (useCheckoutSession as jest.Mock).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
      data: null,
      isError: false,
      error: null,
    });

    render(<CheckoutPanel sessionId="sess-001" />, { wrapper: createWrapper() });
    expect(screen.getByText('Processing...')).toBeVisible();
  });

  it('shows error state on checkout failure', async () => {
    (useCheckoutSession as jest.Mock).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      data: null,
      isError: true,
      error: new Error('Insufficient wallet balance'),
    });

    render(<CheckoutPanel sessionId="sess-001" />, { wrapper: createWrapper() });
    expect(screen.getByText('Insufficient wallet balance')).toBeVisible();
  });
});
```

**Tests for Sessions API:**
```ts
// frontend/src/api/sessions.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchSession, checkoutSession, fetchInvoice, printInvoicePdf } from './sessions';

global.fetch = vi.fn();

describe('sessions API', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('fetchSession calls correct endpoint', async () => {
    const mockSession = { id: 'sess-001', locked_rate_paise: 5000 };
    (fetch as vi.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSession),
    });

    const result = await fetchSession('sess-001', 'token-123');

    expect(fetch).toHaveBeenCalledWith('/api/sessions/sess-001', {
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer token-123' },
    });
    expect(result).toEqual(mockSession);
  });

  it('fetchSession throws on error', async () => {
    (fetch as vi.Mock).mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    });

    await expect(fetchSession('sess-001', 'token')).rejects.toThrow('Failed to fetch session: 404 Not Found');
  });

  it('checkoutSession posts correct body', async () => {
    const mockInvoice = { id: 'inv-001', total_paise: 50000 };
    (fetch as vi.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockInvoice),
    });

    const result = await checkoutSession('sess-001', { payment_method: 'CARD' }, 'token-123');

    expect(fetch).toHaveBeenCalledWith('/api/sessions/sess-001/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer token-123' },
      body: JSON.stringify({ payment_method: 'CARD' }),
    });
    expect(result).toEqual(mockInvoice);
  });

  it('printInvoicePdf opens blob in new window', async () => {
    const mockBlob = new Blob(['html'], { type: 'text/html' });
    (fetch as vi.Mock).mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(mockBlob),
    });

    const openMock = vi.fn();
    vi.stubGlobal('window', { open: openMock, URL: { createObjectURL: vi.fn(() => 'blob:url') } });

    await printInvoicePdf('inv-001', 'token');

    expect(fetch).toHaveBeenCalledWith('/api/invoices/inv-001/pdf', {
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer token' },
    });
    expect(openMock).toHaveBeenCalledWith('blob:url', '_blank');
  });
});
```

---

### Task 9: Update Feature Flag Export (if needed)

**Files:** Verify `frontend/src/store/featureFlagStore.ts` has all required flags
**Note:** The existing flags include `enable_pos` which controls POS. Checkout should work even if POS is disabled (for sessions with only time charges). No changes needed - the checkout panel is not feature-flagged separately.

---

### Task 10: Run Tests and Verify

**Commands:**
```bash
# Frontend tests
cd frontend && npm test -- --run

# Backend tests (for checkout endpoint)
cd backend && python -m pytest backend/tests/test_checkout.py -v

# Lint
cd frontend && npm run lint
cd backend && ruff check .
cd backend && mypy --strict backend/
```

---

## Verification Checklist

After implementation, verify:

- [ ] **PREVIEW state loads**: Session detail + POS items fetched, invoice breakdown displayed
- [ ] **Payment method selector**: All 4 methods (CASH, CARD, WALLET, PACKAGE) selectable
- [ ] **Confirm Payment**: POSTs to `/api/sessions/{id}/checkout` with selected method
- [ ] **COMPLETE state shows**: Server-returned invoice with all line items, totals, payment method
- [ ] **Print Receipt**: Opens `/api/invoices/{id}/pdf` in new tab, triggers `window.print()`
- [ ] **New Session button**: Resets panel to PREVIEW state (parent drawer handles close)
- [ ] **Error handling**: Network errors shown with retry option
- [ ] **Loading states**: Skeletons shown during fetch, spinner on confirm
- [ ] **Currency formatting**: All amounts show `Rs. X.XX` via `formatPaise`
- [ ] **POS items displayed**: In PREVIEW (from `useSessionItems`) and COMPLETE (from invoice line_items)
- [ ] **Package credit & discounts**: Show correctly when present in invoice
- [ ] **Mobile responsive**: Works at 375px width (check tab layout, button stacking)
- [ ] **Dark theme**: `slate-900` backgrounds, `text-emerald-400` for money, blue accents

---

## Spec Coverage Check

From SRS §4.4 Billing Engine and §4.19 Receipts and Printing:

| Requirement | Covered By |
|-------------|------------|
| FR-BILL-008: Invoice itemizes time charge, package usage, discount, POS items, total | Task 4 `InvoicePanel` shows all breakdown rows |
| FR-BILL-009: Staff can mark payment as CASH, CARD, WALLET, PACKAGE | Task 5 `CheckoutPanel` payment method selector |
| FR-PRINT-003: Receipt includes seat, customer, times, duration, time charge, package, discount, POS items, total, payment method | Task 4 `InvoicePanel` + Task 7 `printInvoicePdf` |
| NFR-DATA-002: Paise integer arithmetic, display conversion only at UI | Task 1 `formatPaise` utility used everywhere |

---

## Execution Handoff

**Plan complete and saved to:** `docs/superpowers/plans/2026-07-09-feature-3-2-2-checkout-invoice-panel.md`

**Two execution options:**

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
   - REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`

2. **Inline Execution** - Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review

**Which approach?**
