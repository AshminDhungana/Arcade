import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ShiftModal } from '@/components/ShiftModal';
import type { ShiftCurrentResponse } from '@/types/shift';

const OPEN_CURRENT: ShiftCurrentResponse = {
  shift: {
    id: 's1',
    opened_by_staff_id: 'cashier-1',
    closed_by_staff_id: null,
    opened_at: '2026-08-13T10:00:00Z',
    closed_at: null,
    float_paise: 5000,
    counted_paise: null,
    status: 'OPEN',
  },
  session_count: 3,
  total_revenue_paise: 2500,
  average_duration_seconds: 1800,
  expected_cash_paise: 7500,
};

type ShiftMutateOpts = { onSuccess?: () => void; onError?: (e: Error) => void };
let openShiftMutate: (paise: number, opts?: ShiftMutateOpts) => void;
let closeShiftMutate: (paise: number, opts?: ShiftMutateOpts) => void;
let currentData: ShiftCurrentResponse | null;
let thresholdPaise = '5000';

vi.mock('@/api/shifts', () => ({
  useCurrentShift: () => ({ data: currentData, isPending: false }),
  useOpenShift: () => ({
    mutate: (paise: number, opts?: ShiftMutateOpts) => openShiftMutate(paise, opts),
    isPending: false,
  }),
  useCloseShift: () => ({
    mutate: (paise: number, opts?: ShiftMutateOpts) => closeShiftMutate(paise, opts),
    isPending: false,
  }),
}));

vi.mock('@/api/settings', () => ({
  useSettings: () => ({ data: { shift_cash_variance_threshold: thresholdPaise } }),
}));

vi.mock('@/store/toastStore', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

beforeEach(() => {
  currentData = null;
  thresholdPaise = '5000';
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ShiftModal', () => {
  it('shows the open form when no shift is open', () => {
    currentData = null;
    render(<ShiftModal open onClose={() => {}} />);
    expect(screen.getByLabelText(/cash float/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /open shift/i })).toBeInTheDocument();
  });

  it('opens a shift with the float converted to paise', async () => {
    currentData = null;
    let received: number | undefined;
    openShiftMutate = (paise: number) => {
      received = paise;
    };
    render(<ShiftModal open onClose={() => {}} />);
    fireEvent.change(screen.getByLabelText(/cash float/i), { target: { value: '50' } });
    fireEvent.click(screen.getByRole('button', { name: /open shift/i }));
    expect(received).toBe(5000);
  });

  it('shows live totals when a shift is open', () => {
    currentData = OPEN_CURRENT;
    render(<ShiftModal open onClose={() => {}} />);
    expect(screen.getByText('Rs. 25.00')).toBeInTheDocument(); // revenue
    expect(screen.getByText('3')).toBeInTheDocument(); // sessions
    expect(screen.getByText('30 min')).toBeInTheDocument(); // avg duration
  });

  it('closes the shift with counted cash in paise', async () => {
    currentData = OPEN_CURRENT;
    let received: number | undefined;
    closeShiftMutate = (paise: number) => {
      received = paise;
    };
    render(<ShiftModal open onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /close shift/i }));
    fireEvent.change(screen.getByLabelText(/counted cash/i), { target: { value: '76' } });
    fireEvent.click(screen.getByRole('button', { name: /close shift/i }));
    expect(received).toBe(7600);
  });

  it('shows a warning banner when variance exceeds the threshold', () => {
    currentData = OPEN_CURRENT;
    thresholdPaise = '100';
    render(<ShiftModal open onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /close shift/i }));
    fireEvent.change(screen.getByLabelText(/counted cash/i), { target: { value: '80' } });
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('toasts an error when close is blocked by unprinted invoices', async () => {
    const { toast } = await import('@/store/toastStore');
    currentData = OPEN_CURRENT;
    closeShiftMutate = (_paise: number, opts?: ShiftMutateOpts) => {
      opts?.onError?.(new Error('UNPRINTED_INVOICES_BLOCK_SHIFT_CLOSE:count=1'));
    };
    render(<ShiftModal open onClose={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /close shift/i }));
    fireEvent.click(screen.getByRole('button', { name: /close shift/i }));
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        expect.stringContaining('UNPRINTED_INVOICES_BLOCK_SHIFT_CLOSE'),
      );
    });
  });
});
