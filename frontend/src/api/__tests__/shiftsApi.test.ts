import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  fetchCurrentShift,
  openShift,
  closeShift,
} from '@/api/shifts';

const TOKEN = 'tok';

beforeEach(() => {
  vi.restoreAllMocks();
});

const OPEN_SHIFT = {
  id: 's1',
  opened_by_staff_id: 'cashier-1',
  closed_by_staff_id: null,
  opened_at: '2026-08-13T10:00:00Z',
  closed_at: null,
  float_paise: 5000,
  counted_paise: null,
  status: 'OPEN',
};

describe('shift API', () => {
  it('fetchCurrentShift GETs /shifts/current with auth', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({
          shift: OPEN_SHIFT,
          session_count: 0,
          total_revenue_paise: 0,
          average_duration_seconds: 0,
          expected_cash_paise: 5000,
        }),
        { status: 200 },
      ),
    );
    const res = await fetchCurrentShift(TOKEN);
    expect(res?.shift.id).toBe('s1');
    expect(spy.mock.calls[0][0]).toContain('/shifts/current');
    expect(spy.mock.calls[0][1]?.headers).toMatchObject({
      Authorization: 'Bearer tok',
    });
  });

  it('fetchCurrentShift returns null when no shift is open', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(null), { status: 200 }),
    );
    expect(await fetchCurrentShift(TOKEN)).toBeNull();
  });

  it('openShift POSTs float in paise', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(OPEN_SHIFT), { status: 201 }),
    );
    await openShift(TOKEN, 5000);
    expect(spy.mock.calls[0][0]).toContain('/shifts/open');
    expect(spy.mock.calls[0][1]?.method).toBe('POST');
    expect(JSON.parse(spy.mock.calls[0][1]?.body as string)).toEqual({
      float_paise: 5000,
    });
  });

  it('closeShift POSTs counted cash in paise', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ ...OPEN_SHIFT, status: 'CLOSED', counted_paise: 6500 }),
        { status: 200 },
      ),
    );
    await closeShift(TOKEN, 6500);
    expect(spy.mock.calls[0][0]).toContain('/shifts/close');
    expect(spy.mock.calls[0][1]?.method).toBe('POST');
    expect(JSON.parse(spy.mock.calls[0][1]?.body as string)).toEqual({
      counted_paise: 6500,
    });
  });

  it('closeShift surfaces the backend 409 detail (unprinted gate)', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ detail: 'UNPRINTED_INVOICES_BLOCK_SHIFT_CLOSE:count=1' }),
        { status: 409 },
      ),
    );
    await expect(closeShift(TOKEN, 6500)).rejects.toThrow(
      'UNPRINTED_INVOICES_BLOCK_SHIFT_CLOSE',
    );
  });
});
