// frontend/src/api/invoices.test.ts
import { beforeEach, describe, it, expect, vi } from 'vitest';
import { fetchInvoice, fetchInvoicePdf, checkoutSession } from './invoices';
import type { Invoice } from '@/types/invoice';

const mockToken = 'test-jwt-token';

beforeEach(() => {
  vi.resetAllMocks();
  global.fetch = vi.fn();
});

describe('fetchInvoice', () => {
  it('calls GET /api/invoices/{id} with auth header', async () => {
    const mockInvoice = { id: 'inv_1', total_paise: 5000 } as unknown as Invoice;
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockInvoice),
    } as Response);

    const result = await fetchInvoice('inv_1', mockToken);

    expect(global.fetch).toHaveBeenCalledWith('/api/invoices/inv_1', {
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${mockToken}` },
    });
    expect(result).toEqual(mockInvoice);
  });

  it('throws on non-ok response', async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    } as Response);

    await expect(fetchInvoice('inv_1', mockToken)).rejects.toThrow('Failed to fetch invoice: 404 Not Found');
  });
});

describe('fetchInvoicePdf', () => {
  it('calls GET /api/invoices/{id}/pdf and returns HTML string', async () => {
    const html = '<html>receipt</html>';
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      text: () => Promise.resolve(html),
    } as Response);

    const result = await fetchInvoicePdf('inv_1', mockToken);

    expect(global.fetch).toHaveBeenCalledWith('/api/invoices/inv_1/pdf', {
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${mockToken}` },
    });
    expect(result).toBe(html);
  });
});

describe('checkoutSession', () => {
  it('calls POST /api/sessions/{id}/checkout with payment_method', async () => {
    const mockInvoice = { id: 'inv_1', total_paise: 5000 } as unknown as Invoice;
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockInvoice),
    } as Response);

    const result = await checkoutSession('sess_1', 'CARD', mockToken);

    expect(global.fetch).toHaveBeenCalledWith('/api/sessions/sess_1/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${mockToken}` },
      body: JSON.stringify({ payment_method: 'CARD' }),
    });
    expect(result).toEqual(mockInvoice);
  });
});
