import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { UnprintedInvoices } from '@/components/UnprintedInvoices';
import { useUnprintedInvoices } from '@/api/invoices';

vi.mock('@/api/invoices', () => ({
  useUnprintedInvoices: vi.fn(),
  useReprintInvoice: () => ({ mutate: vi.fn(), isPending: false }),
  useMarkInvoicePrinted: () => ({ mutate: vi.fn(), isPending: false }),
  useForceCloseUnprinted: () => ({ mutate: vi.fn(), isPending: false }),
  printInvoicePdf: vi.fn(),
}));
vi.mock('@/store/authStore', () => ({ useAuthStore: () => ({ accessToken: 'tok' }) }));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient();
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>;
}

describe('UnprintedInvoices', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the empty state when no unprinted invoices', () => {
    (useUnprintedInvoices as unknown as vi.Mock).mockReturnValue({ data: [], isLoading: false });
    render(wrap(<UnprintedInvoices />));
    expect(screen.getByText(/no unprinted invoices/i)).toBeTruthy();
  });

  it('renders a row with Reprint / Force close actions', async () => {
    (useUnprintedInvoices as unknown as vi.Mock).mockReturnValue({
      data: [{ id: 'inv-1', print_status: 'FAILED', total_paise: 500, session_id: 's1' }],
      isLoading: false,
    });
    render(wrap(<UnprintedInvoices />));
    expect(await screen.findByText(/inv-1/)).toBeTruthy();
    expect(screen.getByText(/reprint/i)).toBeTruthy();
    expect(screen.getByText(/force close/i)).toBeTruthy();
  });
});
