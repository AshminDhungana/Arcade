// frontend/src/api/invoices.test.ts
import { beforeEach, describe, it, expect, vi } from 'vitest';
import { fetchInvoice, fetchInvoicePdf, checkoutSession } from './invoices';

const mockToken = 'test-jwt-token';

beforeEach(() => {
  vi.resetAllMocks();
  global.fetch = vi.fn();
});

describe('fetchInvoice', () => {
  it('calls GET /api/invoices/{id} with auth header', async () => {
    const mockInvoice = { id: 'inv_1', total_paise: 5000 } as any;
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockInvoice),
    });

    const result = await fetchInvoice('inv_1', mockToken);

    expect(global.fetch).toHaveBeenCalledWith('/api/invoices/inv_1', {
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${mockToken}` },
    });
    expect(result).toEqual(mockInvoice);
  });

  it('throws on non-ok response', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    });

    await expect(fetchInvoice('inv_1', mockToken)).rejects.toThrow('Failed to fetch invoice: 404 Not Found');
  });
});

describe('fetchInvoicePdf', () => {
  it('calls GET /api/invoices/{id}/pdf and returns HTML string', async () => {
    const html = '<html>receipt</html>';
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      text: () => Promise.resolve(html),
    });

    const result = await fetchInvoicePdf('inv_1', mockToken);

    expect(global.fetch).toHaveBeenCalledWith('/api/invoices/inv_1/pdf', {
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${mockToken}` },
    });
    expect(result).toBe(html);
  });
});

describe('checkoutSession', () => {
  it('calls POST /api/sessions/{id}/checkout with payment_method', async () => {
    const mockInvoice = { id: 'inv_1', total_paise: 5000 } as any;
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockInvoice),
    });

    const result = await checkoutSession('sess_1', 'CARD', mockToken);

    expect(global.fetch).toHaveBeenCalledWith('/api/sessions/sess_1/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${mockToken}` },
      body: JSON.stringify({ payment_method: 'CARD' }),
    });
    expect(result).toEqual(mockInvoice);
  });
});
