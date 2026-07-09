// frontend/src/components/invoice/CheckoutPanel.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CheckoutPanel } from './CheckoutPanel';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock hooks
vi.mock('@/api/sessions', () => ({
  useSession: vi.fn(),
}));

vi.mock('@/api/pos', () => ({
  useSessionItems: vi.fn(),
  useMenu: vi.fn(),
}));

vi.mock('@/api/invoices', () => ({
  useCheckout: vi.fn(),
  printInvoicePdf: vi.fn(),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn((selector) => selector({ accessToken: 'test-token' })),
}));

import { useSession } from '@/api/sessions';
import { useSessionItems, useMenu } from '@/api/pos';
import { useCheckout, printInvoicePdf } from '@/api/invoices';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockSession = {
  id: 'sess_1',
  seat_id: 'seat_1',
  member_id: 'member_1',
  shift_id: 'shift_1',
  status: 'ACTIVE',
  started_at: new Date(Date.now() - 7200 * 1000).toISOString(), // 2 hours ago
  paused_at: null,
  total_paused_seconds: 0,
  locked_rate_paise: 200, // Rs. 2.00 / min
  locked_pricing_model: 'PER_MINUTE',
  package_entitlement_id: null,
  promotion_id: null,
  discount_paise: 3000,
  payment_method: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockPOSItems = [
  {
    id: 'pos_li_1',
    session_id: 'sess_1',
    menu_item_id: 'cola',
    quantity: 2,
    unit_price_paise: 4000,
    added_at: new Date().toISOString(),
  },
];

const mockMenu = [
  {
    id: 'cola',
    name: 'Coca Cola',
    category: 'Drinks',
    price_paise: 4000,
    stock_quantity: 10,
    low_stock_threshold: 2,
    is_available: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockInvoice = {
  id: 'inv_completed_1',
  session_id: 'sess_1',
  member_id: 'member_1',
  shift_id: 'shift_1',
  time_charge_paise: 24000, // 120 minutes * 200 paise
  package_credit_used_paise: 0,
  discount_paise: 3000,
  pos_total_paise: 8000,
  total_paise: 29000,
  payment_method: 'CARD',
  created_at: new Date().toISOString(),
  line_items: [
    {
      id: 'item_1',
      invoice_id: 'inv_completed_1',
      type: 'TIME_CHARGE',
      description: 'Time Charge (PER_MINUTE)',
      quantity: 120,
      unit_price_paise: 200,
      total_paise: 24000,
    },
    {
      id: 'item_2',
      invoice_id: 'inv_completed_1',
      type: 'POS_ITEM',
      description: 'Coca Cola',
      quantity: 2,
      unit_price_paise: 4000,
      total_paise: 8000,
    },
  ],
};

describe('CheckoutPanel', () => {
  const mockMutate = vi.fn();
  const mockClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useSession).mockReturnValue({
      data: mockSession,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSession>);

    vi.mocked(useSessionItems).mockReturnValue({
      data: mockPOSItems,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useSessionItems>);

    vi.mocked(useMenu).mockReturnValue({
      data: mockMenu,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useMenu>);

    vi.mocked(useCheckout).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      data: null,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useCheckout>);
  });

  it('renders loading state when queries are loading', () => {
    vi.mocked(useSession).mockReturnValue({ isLoading: true } as unknown as ReturnType<typeof useSession>);
    render(<CheckoutPanel sessionId="sess_1" onClose={mockClose} />, { wrapper: createWrapper() });
    expect(screen.getByText('Loading checkout breakdown...')).toBeInTheDocument();
  });

  it('renders error state when fetch fails', () => {
    vi.mocked(useSession).mockReturnValue({ isError: true } as unknown as ReturnType<typeof useSession>);
    render(<CheckoutPanel sessionId="sess_1" onClose={mockClose} />, { wrapper: createWrapper() });
    expect(screen.getByText('Failed to load session details')).toBeInTheDocument();
  });

  it('renders preview breakdown with client estimates and maps POS IDs to names', () => {
    render(<CheckoutPanel sessionId="sess_1" onClose={mockClose} />, { wrapper: createWrapper() });

    expect(screen.getByText('Time Charge (PER_MINUTE)')).toBeInTheDocument();
    expect(screen.getByText('Coca Cola')).toBeInTheDocument(); // mapped from menu
    expect(screen.getAllByText('Rs. 240.00').length).toBe(2); // estimate (2h = 120m * Rs. 2.00)
    expect(screen.getAllByText('Rs. 80.00').length).toBe(2); // POS
    expect(screen.getByText('-Rs. 30.00')).toBeInTheDocument(); // Discount
    expect(screen.getByText('Rs. 290.00')).toBeInTheDocument(); // Grand total (240 + 80 - 30)
  });

  it('allows selected payment method toggle and calls checkout mutation', () => {
    render(<CheckoutPanel sessionId="sess_1" onClose={mockClose} />, { wrapper: createWrapper() });

    const cardButton = screen.getByText('Card');
    fireEvent.click(cardButton);

    const payButton = screen.getByText('Confirm Payment & Checkout');
    fireEvent.click(payButton);

    expect(mockMutate).toHaveBeenCalledWith(
      { sessionId: 'sess_1', paymentMethod: 'CARD' },
      expect.any(Object)
    );
  });

  it('renders completed invoice and fires print and close actions on success', async () => {
    mockMutate.mockImplementationOnce((variables, options) => {
      if (options && options.onSuccess) {
        options.onSuccess(mockInvoice);
      }
    });

    vi.mocked(useCheckout).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      data: mockInvoice,
      isSuccess: true,
    } as unknown as ReturnType<typeof useCheckout>);

    render(<CheckoutPanel sessionId="sess_1" onClose={mockClose} />, {
      wrapper: createWrapper(),
    });

    // Click confirm to trigger checkout and invoke options.onSuccess
    const payButton = screen.getByText('Confirm Payment & Checkout');
    fireEvent.click(payButton);

    // Check complete state indicators
    expect(screen.getByText('Session Checked Out Successfully')).toBeInTheDocument();
    expect(screen.getByText('Card Paid')).toBeInTheDocument();

    // Verify print handler is triggered
    const printBtn = screen.getByText('Print Receipt');
    fireEvent.click(printBtn);
    expect(printInvoicePdf).toHaveBeenCalledWith('inv_completed_1', 'test-token');

    // Verify close handler is triggered
    const closeBtn = screen.getByText('New Session');
    fireEvent.click(closeBtn);
    expect(mockClose).toHaveBeenCalled();
  });
});
