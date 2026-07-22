import { describe, it, expect, vi, beforeEach } from 'vitest';
import { listUnprinted, reprintInvoice, markInvoicePrinted } from '@/api/invoices';

const TOKEN = 'tok';

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('invoice print-gate API', () => {
  it('listUnprinted fetches /invoices/unprinted', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([{ id: 'i1', print_status: 'FAILED' }]), { status: 200 }),
    );
    const res = await listUnprinted(TOKEN);
    expect(res).toHaveLength(1);
    expect(spy.mock.calls[0][0]).toContain('/invoices/unprinted');
  });

  it('reprintInvoice posts to /invoices/{id}/reprint', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ id: 'i1', print_status: 'PRINTED' }), { status: 200 }),
    );
    await reprintInvoice('i1', TOKEN);
    expect(spy.mock.calls[0][0]).toContain('/invoices/i1/reprint');
    expect(spy.mock.calls[0][1]?.method).toBe('POST');
  });

  it('markInvoicePrinted posts to /invoices/{id}/mark-printed', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ id: 'i1', print_status: 'PRINTED' }), { status: 200 }),
    );
    await markInvoicePrinted('i1', TOKEN);
    expect(spy.mock.calls[0][0]).toContain('/invoices/i1/mark-printed');
  });
});
