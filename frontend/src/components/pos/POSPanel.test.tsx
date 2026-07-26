import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { POSPanel } from './POSPanel';
import type { ReactNode } from 'react';

// Mock the feature flag store
vi.mock('@/store/featureFlagStore', () => ({
  useFeatureFlagStore: vi.fn((selector) => selector({
    flags: { enable_pos: true, enable_inventory: false },
    setFlags: vi.fn(),
    clear: vi.fn(),
  })),
}));

// Mock the POS API hooks
const mockMenuData = [
  { id: 'm1', name: 'Cola', category: 'DRINKS', price_paise: 4000, is_available: true, stock_quantity: 10, low_stock_threshold: 5, created_at: '', updated_at: '' },
  { id: 'm2', name: 'Burger', category: 'FOOD', price_paise: 12000, is_available: false, stock_quantity: 0, low_stock_threshold: 5, created_at: '', updated_at: '' },
];

const mockSessionItemsData: never[] = [];

const mockAddMutate = vi.fn();
const mockRemoveMutate = vi.fn();

vi.mock('@/api/pos', () => ({
  useMenu: () => ({
    data: mockMenuData,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useSessionItems: () => ({
    data: mockSessionItemsData,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useAddPosItem: () => ({
    mutate: mockAddMutate,
    isPending: false,
    isError: false,
    error: null,
  }),
  useRemovePosItem: () => ({
    mutate: mockRemoveMutate,
    isPending: false,
    isError: false,
    error: null,
  }),
}));

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return ({ children }: { children: ReactNode }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('POSPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAddMutate.mockClear();
    mockRemoveMutate.mockClear();
  });

  it('renders null when enable_pos flag is false', async () => {
    vi.resetModules();
    vi.doMock('@/store/featureFlagStore', () => ({
      useFeatureFlagStore: vi.fn((selector) => selector({
        flags: { enable_pos: false, enable_inventory: false },
        setFlags: vi.fn(),
        clear: vi.fn(),
      })),
    }));
    const { POSPanel: FreshPOSPanel } = await import('./POSPanel');
    const { unmount } = render(<FreshPOSPanel sessionId="sess-1" />, { wrapper: makeWrapper() });
    unmount();
    expect(screen.queryByTestId('pos-panel')).not.toBeInTheDocument();
  });

  it('renders MenuGrid and SessionTab when POS enabled', () => {
    render(<POSPanel sessionId="sess-1" />, { wrapper: makeWrapper() });
    expect(screen.getByTestId('pos-panel')).toBeInTheDocument();
    expect(screen.getByText('Menu')).toBeInTheDocument();
    expect(screen.getByText('Session Tab')).toBeInTheDocument();
  });

  it('MenuItemCard is disabled when is_available=false', () => {
    render(<POSPanel sessionId="sess-1" />, { wrapper: makeWrapper() });
    const burgerBtn = screen.getByRole('button', { name: /burger/i });
    expect(burgerBtn).toBeDisabled();
    // Disabled style includes opacity-50
    expect(burgerBtn).toHaveClass('opacity-50');
  });

  it('clicking available item calls addMutation.mutate', async () => {
    render(<POSPanel sessionId="sess-1" />, { wrapper: makeWrapper() });
    const colaBtn = screen.getByRole('button', { name: /cola/i });
    fireEvent.click(colaBtn);
    await waitFor(() => expect(mockAddMutate).toHaveBeenCalledWith({
      session_id: 'sess-1',
      menu_item_id: 'm1',
      quantity: 1,
    }));
  });
});
