import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExpensesTab } from './ExpensesTab';
import { useAuthStore } from '@/store/authStore';
import type { ReactNode } from 'react';
import type { Expense } from '@/types/settings';

const MOCK_EXPENSES: Expense[] = [
  {
    id: 'e1',
    date: '2026-08-15',
    category: 'RENT',
    amount_paise: 5000000,
    note: 'August rent',
    logged_by_staff_id: 'staff1',
    logged_by_staff_name: 'Admin User',
    created_at: '2026-08-15T10:00:00Z',
  },
  {
    id: 'e2',
    date: '2026-08-10',
    category: 'ELECTRICITY',
    amount_paise: 150000,
    note: 'Power bill',
    logged_by_staff_id: 'staff1',
    logged_by_staff_name: 'Admin User',
    created_at: '2026-08-10T10:00:00Z',
  },
];

// Hoisted mock state - use an object with mutable array to avoid closure issues
const mockState = {
  expenses: [] as Expense[],
  createExpenseFn: vi.fn(),
  deleteExpenseFn: vi.fn(),
};

// Initialize with test data
mockState.expenses.push(...MOCK_EXPENSES);

// Hoisted isPending refs
const isPendingRefs = {
  createExpense: { current: false },
  deleteExpense: { current: false },
};

vi.mock('@/api/settings', () => ({
  useExpenses: () => ({
    data: mockState.expenses,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreateExpense: () => ({
    mutateAsync: mockState.createExpenseFn,
    get isPending() {
      return isPendingRefs.createExpense.current;
    },
  }),
  useDeleteExpense: () => ({
    mutateAsync: mockState.deleteExpenseFn,
    get isPending() {
      return isPendingRefs.deleteExpense.current;
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

describe('ExpensesTab', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'test-token' });
    // Mutate the array instead of reassigning to avoid closure issues
    mockState.expenses.length = 0;
    mockState.expenses.push(...MOCK_EXPENSES);
    mockState.createExpenseFn = vi.fn();
    mockState.deleteExpenseFn = vi.fn();
    isPendingRefs.createExpense.current = false;
    isPendingRefs.deleteExpense.current = false;
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders expenses heading and add button', () => {
    render(<ExpensesTab />, { wrapper: makeWrapper() });

    expect(screen.getByRole('heading', { name: /expenses/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /add expense/i })).toBeInTheDocument();
  });

  it('renders expenses table with category badges and amounts', () => {
    render(<ExpensesTab />, { wrapper: makeWrapper() });

    expect(screen.getByText('Rent')).toBeInTheDocument();
    expect(screen.getByText('Electricity')).toBeInTheDocument();
    // formatPaise returns "Rs. 50000.00" (no comma separator)
    expect(screen.getByText(/rs\. 50000\.00/i)).toBeInTheDocument();
    expect(screen.getByText(/rs\. 1500\.00/i)).toBeInTheDocument();
    expect(screen.getByText('August rent')).toBeInTheDocument();
    expect(screen.getByText('Power bill')).toBeInTheDocument();
  });

  it('shows EmptyState when no expenses exist', () => {
    // Mutate array instead of reassigning
    mockState.expenses.length = 0;
    render(<ExpensesTab />, { wrapper: makeWrapper() });

    expect(screen.getByText(/no expenses yet/i)).toBeInTheDocument();
  });

  it('adds a new expense via modal and the row appears in the table', async () => {
    const newExpense: Expense = {
      id: 'e3',
      date: '2026-08-18',
      category: 'WAGES',
      amount_paise: 2500000,
      note: 'Staff wages',
      logged_by_staff_id: 'staff1',
      logged_by_staff_name: 'Admin User',
      created_at: '2026-08-18T10:00:00Z',
    };

    let resolveCreate: (v: Expense) => void;
    const createPromise = new Promise<Expense>((resolve) => {
      resolveCreate = resolve;
    });

    // Mutate array instead of reassigning
    mockState.expenses.length = 0;
    mockState.createExpenseFn = vi.fn().mockReturnValue(createPromise);

    const { rerender } = render(<ExpensesTab />, { wrapper: makeWrapper() });

    // Click "Add Expense" button
    const addExpenseBtn = screen.getByRole('button', { name: /add expense/i });
    await act(async () => { await addExpenseBtn.click(); });

    // Wait for modal to open
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /add expense/i })).toBeInTheDocument();
    });

    // Fill the modal form using fireEvent
    const dateInput = screen.getByLabelText(/date/i);
    const categorySelect = screen.getByLabelText(/category/i);
    const amountInput = screen.getByLabelText(/amount \(in currency units/i);
    const noteInput = screen.getByLabelText(/note \(optional\)/i);

    fireEvent.change(dateInput, { target: { value: '2026-08-18' } });
    fireEvent.change(categorySelect, { target: { value: 'WAGES' } });
    fireEvent.change(amountInput, { target: { value: '25000.00' } });
    fireEvent.change(noteInput, { target: { value: 'Staff wages' } });

    // Submit the form by clicking the submit button
    const submitBtn = screen.getByRole('button', { name: /^create$/i });
    await act(async () => { await fireEvent.click(submitBtn); });

    // Wait for the create mutation to be called
    await waitFor(() => expect(mockState.createExpenseFn).toHaveBeenCalled());

    // Resolve the create promise with the new expense
    resolveCreate!(newExpense);
    isPendingRefs.createExpense.current = false;

    // Update the list data to simulate query invalidation - mutate array
    mockState.expenses.length = 0;
    mockState.expenses.push(newExpense);

    // Re-render to reflect the updated list
    rerender(<ExpensesTab />);

    // Verify the new row appears
    await waitFor(() => {
      expect(screen.getByText('Wages')).toBeInTheDocument();
      expect(screen.getByText(/rs\. 25000\.00/i)).toBeInTheDocument();
      expect(screen.getByText('Staff wages')).toBeInTheDocument();
    });
  });

  it('deletes an expense via confirm dialog', async () => {
    let resolveDelete: (v: void) => void;
    const deletePromise = new Promise<void>((resolve) => {
      resolveDelete = resolve;
    });

    // Ensure array has test data
    mockState.expenses.length = 0;
    mockState.expenses.push(...MOCK_EXPENSES);
    mockState.deleteExpenseFn = vi.fn().mockReturnValue(deletePromise);

    const { rerender } = render(<ExpensesTab />, { wrapper: makeWrapper() });

    // Find the delete button for the first expense and click it
    const deleteBtn = screen.getByRole('button', { name: /delete expense e1/i });
    await act(async () => { await fireEvent.click(deleteBtn); });

    // Confirm dialog appears - click confirm
    const confirmBtn = screen.getByRole('button', { name: /^delete$/i });
    await act(async () => { await fireEvent.click(confirmBtn); });

    // Resolve the mutation
    resolveDelete!();
    isPendingRefs.deleteExpense.current = false;

    // Update list data to simulate query invalidation - mutate array
    mockState.expenses.length = 0;
    mockState.expenses.push(MOCK_EXPENSES[1]);

    // Re-render
    rerender(<ExpensesTab />);

    // Assert the deleted expense is gone
    await waitFor(() => {
      expect(screen.queryByText('August rent')).not.toBeInTheDocument();
      expect(screen.queryByText(/rs\. 50000\.00/i)).not.toBeInTheDocument();
    });
  });

  it('shows error toast on 403 when creating expense', async () => {
    mockState.expenses = [];
    mockState.createExpenseFn = vi.fn().mockRejectedValue(new Error('403 Forbidden: Admin required'));

    render(<ExpensesTab />, { wrapper: makeWrapper() });

    const addExpenseBtn = screen.getByRole('button', { name: /add expense/i });
    await act(async () => { await addExpenseBtn.click(); });

    const dateInput = screen.getByLabelText(/date/i);
    const categorySelect = screen.getByLabelText(/category/i);
    const amountInput = screen.getByLabelText(/amount \(in currency units/i);

    await act(async () => {
      fireEvent.change(dateInput, { target: { value: '2026-08-18' } });
      fireEvent.change(categorySelect, { target: { value: 'RENT' } });
      fireEvent.change(amountInput, { target: { value: '5000.00' } });
    });

    const submitBtn = screen.getByRole('button', { name: /^create$/i });
    await act(async () => { await fireEvent.click(submitBtn); });

    await waitFor(() => expect(mockState.createExpenseFn).toHaveBeenCalled());

    const { toast } = await import('@/store/toastStore');
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Admin required');
    });
  });

  it('shows validation error for amount less than or equal to 0', async () => {
    mockState.expenses.length = 0;

    render(<ExpensesTab />, { wrapper: makeWrapper() });

    const addExpenseBtn = screen.getByRole('button', { name: /add expense/i });
    await act(async () => { await addExpenseBtn.click(); });

    // Wait for modal to open - check for modal title (h2)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /add expense/i })).toBeInTheDocument();
    });

    // Fill the modal form using fireEvent
    const dateInput = screen.getByLabelText(/date/i);
    const categorySelect = screen.getByLabelText(/category/i);
    const amountInput = screen.getByLabelText(/amount \(in currency units/i);

    fireEvent.change(dateInput, { target: { value: '2026-08-18' } });
    fireEvent.change(categorySelect, { target: { value: 'RENT' } });
    fireEvent.change(amountInput, { target: { value: '0' } });

    // Submit the form by submitting the form element directly
    const submitBtn = screen.getByRole('button', { name: /^create$/i });
    const form = submitBtn.closest('form');
    if (form) {
      fireEvent.submit(form);
    }

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText(/amount must be greater than 0/i)).toBeInTheDocument();
    });

    // Mutation should not be called
    expect(mockState.createExpenseFn).not.toHaveBeenCalled();
  });

  it('shows validation error for missing date', async () => {
    mockState.expenses.length = 0;

    render(<ExpensesTab />, { wrapper: makeWrapper() });

    const addExpenseBtn = screen.getByRole('button', { name: /add expense/i });
    await act(async () => { await addExpenseBtn.click(); });

    // Wait for modal to open - check for modal title (h2)
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /add expense/i })).toBeInTheDocument();
    });

    // Fill the modal form using fireEvent
    const categorySelect = screen.getByLabelText(/category/i);
    const amountInput = screen.getByLabelText(/amount \(in currency units/i);
    const dateInput = screen.getByLabelText(/date/i);

    fireEvent.change(categorySelect, { target: { value: 'RENT' } });
    fireEvent.change(amountInput, { target: { value: '5000.00' } });
    // Clear the date to test "missing date" validation
    fireEvent.change(dateInput, { target: { value: '' } });

    // Submit the form by submitting the form element directly
    const submitBtn = screen.getByRole('button', { name: /^create$/i });
    const form = submitBtn.closest('form');
    if (form) {
      fireEvent.submit(form);
    }

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText(/date is required/i)).toBeInTheDocument();
    });

    // Mutation should not be called
    expect(mockState.createExpenseFn).not.toHaveBeenCalled();
  });
});
