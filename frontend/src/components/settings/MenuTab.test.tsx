import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MenuTab } from './MenuTab';
import { useAuthStore } from '@/store/authStore';
import type { ReactNode } from 'react';
import type { MenuItem } from '@/types/settings';

const ITEM: MenuItem = {
  id: 'm1',
  name: 'Cola',
  category: 'Beverages',
  price_paise: 25050,
  stock_quantity: 50,
  low_stock_threshold: 10,
  is_available: true,
};

const ITEM_UNAVAILABLE: MenuItem = { ...ITEM, is_available: false };

// Hoisted mock state
const mockState = {
  items: [] as MenuItem[],
  createFn: vi.fn(),
  updateFn: vi.fn(),
  deleteFn: vi.fn(),
};

// Hoisted isPending refs
const isPendingRefs = {
  create: { current: false },
  update: { current: false },
  delete: { current: false },
};

vi.mock('@/api/settings', () => ({
  useMenuItems: () => ({
    data: mockState.items,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreateMenuItem: () => ({
    mutateAsync: mockState.createFn,
    get isPending() {
      return isPendingRefs.create.current;
    },
  }),
  useUpdateMenuItem: () => ({
    mutateAsync: mockState.updateFn,
    get isPending() {
      return isPendingRefs.update.current;
    },
  }),
  useDeleteMenuItem: () => ({
    mutateAsync: mockState.deleteFn,
    get isPending() {
      return isPendingRefs.delete.current;
    },
  }),
}));

vi.mock('@/store/toastStore', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
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

describe('MenuTab', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'test-token' });
    mockState.items = [ITEM];
    mockState.createFn = vi.fn();
    mockState.updateFn = vi.fn();
    mockState.deleteFn = vi.fn();
    isPendingRefs.create.current = false;
    isPendingRefs.update.current = false;
    isPendingRefs.delete.current = false;
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('renders the menu table with name, category, price, and availability badge', () => {
    render(<MenuTab />, { wrapper: makeWrapper() });

    expect(screen.getByText('Cola')).toBeInTheDocument();
    expect(screen.getByText('Beverages')).toBeInTheDocument();
    expect(screen.getByText('Rs. 250.50')).toBeInTheDocument();
    // "Available" appears twice: the column header and the row badge
    expect(screen.getAllByText('Available')).toHaveLength(2);
  });

  it('toggles availability inline and updates the row to unavailable', async () => {
    let resolveUpdate: (v: MenuItem) => void;
    const updatePromise = new Promise<MenuItem>((resolve) => {
      resolveUpdate = resolve;
    });

    mockState.items = [ITEM];
    mockState.updateFn = vi.fn().mockReturnValue(updatePromise);

    const { rerender } = render(<MenuTab />, { wrapper: makeWrapper() });

    // Toggle the availability switch
    const toggle = screen.getByRole('switch', {
      name: /toggle availability for cola/i,
    });
    await act(async () => {
      await fireEvent.click(toggle);
    });

    // Assert the update mutation was called with the correct payload
    await waitFor(() =>
      expect(mockState.updateFn).toHaveBeenCalledWith({
        id: 'm1',
        data: { is_available: false },
      }),
    );

    // Resolve the mutation; reflect the unavailable state in the list
    resolveUpdate!(ITEM_UNAVAILABLE);
    isPendingRefs.update.current = false;
    mockState.items = [ITEM_UNAVAILABLE];

    rerender(<MenuTab />);

    await waitFor(() => {
      expect(screen.getByText('Unavailable')).toBeInTheDocument();
    });
    // Only the column header remains "Available" — the row badge flipped
    expect(screen.getAllByText('Available')).toHaveLength(1);
  });

  it('adds a new menu item via modal and the row appears in the table', async () => {
    const newItem: MenuItem = {
      id: 'm2',
      name: 'Fries',
      category: 'Snacks',
      price_paise: 9900,
      stock_quantity: null,
      low_stock_threshold: null,
      is_available: true,
    };

    let resolveCreate: (v: MenuItem) => void;
    const createPromise = new Promise<MenuItem>((resolve) => {
      resolveCreate = resolve;
    });

    mockState.items = [];
    mockState.createFn = vi.fn().mockReturnValue(createPromise);

    const { rerender } = render(<MenuTab />, { wrapper: makeWrapper() });

    const addBtn = screen.getByRole('button', { name: /add item/i });
    await act(async () => {
      await addBtn.click();
    });

    const nameInput = screen.getByLabelText(/name/i);
    const categoryInput = screen.getByLabelText(/category/i);
    const priceInput = screen.getByLabelText(/price/i);

    await act(async () => {
      fireEvent.change(nameInput, { target: { value: 'Fries' } });
      fireEvent.change(categoryInput, { target: { value: 'Snacks' } });
      fireEvent.change(priceInput, { target: { value: '99' } });
    });

    const submitBtn = screen.getByRole('button', { name: /^create$/i });
    await act(async () => {
      await fireEvent.click(submitBtn);
    });

    await waitFor(() =>
      expect(mockState.createFn).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Fries',
          category: 'Snacks',
          price_paise: 9900,
          is_available: true,
        }),
      ),
    );

    resolveCreate!(newItem);
    isPendingRefs.create.current = false;
    mockState.items = [newItem];

    rerender(<MenuTab />);

    await waitFor(() => {
      expect(screen.getByText('Fries')).toBeInTheDocument();
    });
  });

  it('deletes a menu item via confirm dialog and the row disappears', async () => {
    let resolveDelete: (v: void) => void;
    const deletePromise = new Promise<void>((resolve) => {
      resolveDelete = resolve;
    });

    mockState.items = [ITEM];
    mockState.deleteFn = vi.fn().mockReturnValue(deletePromise);

    const { rerender } = render(<MenuTab />, { wrapper: makeWrapper() });

    const deleteBtn = screen.getByRole('button', { name: /delete cola/i });
    await act(async () => {
      await deleteBtn.click();
    });

    const confirmBtn = screen.getByRole('button', { name: /^delete$/i });
    await act(async () => {
      await fireEvent.click(confirmBtn);
    });

    await waitFor(() => expect(mockState.deleteFn).toHaveBeenCalledWith('m1'));

    resolveDelete!(undefined);
    isPendingRefs.delete.current = false;
    mockState.items = [];

    rerender(<MenuTab />);

    await waitFor(() => {
      expect(screen.queryByText('Cola')).not.toBeInTheDocument();
    });
  });

  it('shows error toast on 403 when creating a menu item', async () => {
    mockState.items = [];
    mockState.createFn = vi.fn().mockRejectedValue(
      new Error('403 Forbidden: Admin required'),
    );

    render(<MenuTab />, { wrapper: makeWrapper() });

    const addBtn = screen.getByRole('button', { name: /add item/i });
    await act(async () => {
      await addBtn.click();
    });

    const nameInput = screen.getByLabelText(/name/i);
    const priceInput = screen.getByLabelText(/price/i);

    await act(async () => {
      fireEvent.change(nameInput, { target: { value: 'Test Item' } });
      fireEvent.change(priceInput, { target: { value: '10' } });
    });

    const submitBtn = screen.getByRole('button', { name: /^create$/i });
    await act(async () => {
      await fireEvent.click(submitBtn);
    });

    await waitFor(() => expect(mockState.createFn).toHaveBeenCalled());

    const { toast } = await import('@/store/toastStore');
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Admin required');
    });
  });

  it('shows EmptyState when no menu items exist', () => {
    mockState.items = [];

    render(<MenuTab />, { wrapper: makeWrapper() });

    expect(screen.getByText(/no menu items yet/i)).toBeInTheDocument();
  });
});
