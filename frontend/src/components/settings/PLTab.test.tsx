import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PLTab } from './PLTab';
import type { ReactNode } from 'react';

const MOCK_PL_SUMMARY = {
  period_start: '2026-08-01',
  period_end: '2026-08-31',
  session_revenue_paise: 5000000,
  pos_revenue_paise: 2000000,
  total_revenue_paise: 7000000,
  expenses_by_category: {
    RENT: 3000000,
    ELECTRICITY: 500000,
    WAGES: 2000000,
  },
  total_expenses_paise: 5500000,
  gross_profit_paise: 7000000,
  net_profit_paise: 1500000,
};

vi.mock('@/api/analytics', () => ({
  usePLSummary: () => ({
    data: MOCK_PL_SUMMARY,
    isLoading: false,
    isError: false,
  }),
  usePLMonthly: () => ({
    data: null,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => ({ accessToken: 'test-token' })),
}));

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe('PLTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders P&L heading', () => {
    render(<PLTab />, { wrapper: makeWrapper() });
    expect(screen.getByRole('heading', { name: /profit & loss/i })).toBeInTheDocument();
  });

  it('renders summary cards with revenue, expenses, gross profit, net profit', () => {
    render(<PLTab />, { wrapper: makeWrapper() });
    // formatPaise returns "Rs. 70000.00" (no comma separator)
    // Total Revenue and Gross Profit both show Rs. 70000.00
    expect(screen.getAllByText(/rs\. 70000\.00/i)).toHaveLength(2);
    // Total Expenses shows in card AND in category breakdown total row
    expect(screen.getAllByText(/rs\. 55000\.00/i)).toHaveLength(2);
    expect(screen.getByText(/rs\. 15000\.00/i)).toBeInTheDocument(); // Net Profit
  });

  it('renders category breakdown table', () => {
    render(<PLTab />, { wrapper: makeWrapper() });
    expect(screen.getByText('Rent')).toBeInTheDocument();
    expect(screen.getByText('Electricity')).toBeInTheDocument();
    expect(screen.getByText('Wages')).toBeInTheDocument();
    expect(screen.getByText('Rs. 30000.00')).toBeInTheDocument();
    expect(screen.getByText('Rs. 5000.00')).toBeInTheDocument();
    expect(screen.getByText('Rs. 20000.00')).toBeInTheDocument();
  });

  it('shows month picker for monthly view', () => {
    render(<PLTab />, { wrapper: makeWrapper() });
    // The month picker button shows the current month name (e.g., "August 2026")
    expect(screen.getByRole('button', { name: /august 2026/i })).toBeInTheDocument();
  });
});
