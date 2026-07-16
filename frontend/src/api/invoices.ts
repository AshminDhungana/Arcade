// frontend/src/api/invoices.ts
import type { Invoice, PaymentMethod } from '@/types/invoice';
import { useAuthStore } from '@/store/authStore';

const API_BASE = '/api';

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------

function authHeaders(token: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

/** Fetch a single invoice by ID. */
export async function fetchInvoice(invoiceId: string, token: string | null): Promise<Invoice> {
  const res = await fetch(`${API_BASE}/invoices/${invoiceId}`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch invoice: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as Invoice;
}

/** Fetch print-friendly HTML receipt for an invoice. */
export async function fetchInvoicePdf(invoiceId: string, token: string | null): Promise<string> {
  const res = await fetch(`${API_BASE}/invoices/${invoiceId}/pdf`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch invoice PDF: ${res.status} ${res.statusText}`);
  }
  return (await res.text()) as string;
}

/** Checkout a session — returns the generated invoice. */
export async function checkoutSession(
  sessionId: string,
  paymentMethod: PaymentMethod,
  token: string | null,
): Promise<Invoice> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/checkout`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ payment_method: paymentMethod }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Checkout failed' }));
    throw new Error(err.detail ?? `Checkout failed: ${res.status}`);
  }
  return (await res.json()) as Invoice;
}

// ---------------------------------------------------------------------------
// React Query hooks
// ---------------------------------------------------------------------------

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

/** Hook to fetch invoice by ID. */
export function useInvoice(invoiceId: string) {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['invoice', invoiceId],
    queryFn: () => fetchInvoice(invoiceId, token),
    enabled: !!invoiceId && !!token,
    staleTime: 30 * 1000,
    refetchOnWindowFocus: false,
  });
}

/** Hook to trigger checkout mutation. */
export function useCheckout() {
  const token = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, paymentMethod }: { sessionId: string; paymentMethod: PaymentMethod }) =>
      checkoutSession(sessionId, paymentMethod, token),
    onSuccess: (invoice, _variables) => {
      // Invalidate session lists and seat data
      queryClient.invalidateQueries({ queryKey: ['sessions', 'active'] });
      queryClient.invalidateQueries({ queryKey: ['seats'] });
      // Optionally cache the new invoice
      queryClient.setQueryData(['invoice', invoice.id], invoice);
    },
  });
}

/** Hook to list unprinted invoices. */
export function useUnprintedInvoices() {
  const token = useAuthStore((s) => s.accessToken);
  return useQuery({
    queryKey: ['invoices', 'unprinted'],
    queryFn: () => listUnprinted(token),
    refetchInterval: 15 * 1000,
    refetchOnWindowFocus: false,
  });
}

/** Hook to reprint an invoice. */
export function useReprintInvoice() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (invoiceId: string) => reprintInvoice(invoiceId, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices', 'unprinted'] }),
  });
}

/** Hook to mark an invoice as printed. */
export function useMarkInvoicePrinted() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (invoiceId: string) => markInvoicePrinted(invoiceId, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invoices', 'unprinted'] }),
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

/** List invoices that failed/skipped printing. */
export async function listUnprinted(token: string | null): Promise<Invoice[]> {
  const res = await fetch(`${API_BASE}/invoices/unprinted`, {
    headers: authHeaders(token),
  });
  if (!res.ok) {
    throw new Error(`Failed to list unprinted invoices: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as Invoice[];
}

/** Re-run the thermal print for a FAILED/SKIPPED invoice. */
export async function reprintInvoice(invoiceId: string, token: string | null): Promise<Invoice> {
  const res = await fetch(`${API_BASE}/invoices/${invoiceId}/reprint`, {
    method: 'POST',
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Reprint failed' }));
    throw new Error(err.detail ?? `Reprint failed: ${res.status}`);
  }
  return (await res.json()) as Invoice;
}

/** Mark an invoice as printed (PDF already printed by cashier). */
export async function markInvoicePrinted(invoiceId: string, token: string | null): Promise<Invoice> {
  const res = await fetch(`${API_BASE}/invoices/${invoiceId}/mark-printed`, {
    method: 'POST',
    headers: authHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Mark printed failed' }));
    throw new Error(err.detail ?? `Mark printed failed: ${res.status}`);
  }
  return (await res.json()) as Invoice;
}
