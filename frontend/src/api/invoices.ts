// frontend/src/api/invoices.ts
import type { Invoice } from '@/types/invoice';
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
  paymentMethod: 'CASH' | 'WALLET' | 'CARD',
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
    mutationFn: ({ sessionId, paymentMethod }: { sessionId: string; paymentMethod: 'CASH' | 'WALLET' | 'CARD' }) =>
      checkoutSession(sessionId, paymentMethod, token),
    onSuccess: (invoice, variables) => {
      // Invalidate session lists and seat data
      queryClient.invalidateQueries({ queryKey: ['sessions', 'active'] });
      queryClient.invalidateQueries({ queryKey: ['seats'] });
      // Optionally cache the new invoice
      queryClient.setQueryData(['invoice', invoice.id], invoice);
    },
  });
}
