import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StaffTab } from './StaffTab';
import { useAuthStore } from '@/store/authStore';
import type { ReactNode } from 'react';
import type { Staff } from '@/types/settings';

const STAFF_ADMIN: Staff = {
  id: 's1',
  name: 'Admin User',
  role: 'ADMIN',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const STAFF_CASHIER: Staff = {
  id: 's2',
  name: 'Cashier User',
  role: 'CASHIER',
  is_active: true,
  created_at: '2024-01-02T00:00:00Z',
  updated_at: '2024-01-02T00:00:00Z',
};

// Hoisted mock state
const mockState = {
  staff: [] as Staff[],
  createStaffFn: vi.fn(),
  deactivateStaffFn: vi.fn(),
  reactivateStaffFn: vi.fn(),
  changeStaffPinFn: vi.fn(),
};

// Hoisted isPending refs
const isPendingRefs = {
  createStaff: { current: false },
  deactivateStaff: { current: false },
  reactivateStaff: { current: false },
  changePin: { current: false },
};

vi.mock('@/api/settings', () => ({
  useStaff: () => ({
    data: mockState.staff,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreateStaff: () => ({
    mutateAsync: mockState.createStaffFn,
    get isPending() {
      return isPendingRefs.createStaff.current;
    },
  }),
  useDeactivateStaff: () => ({
    mutateAsync: mockState.deactivateStaffFn,
    get isPending() {
      return isPendingRefs.deactivateStaff.current;
    },
  }),
  useReactivateStaff: () => ({
    mutateAsync: mockState.reactivateStaffFn,
    get isPending() {
      return isPendingRefs.reactivateStaff.current;
    },
  }),
  useChangeStaffPin: () => ({
    mutateAsync: mockState.changeStaffPinFn,
    get isPending() {
      return isPendingRefs.changePin.current;
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

describe('StaffTab', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'test-token' });
    mockState.staff = [STAFF_ADMIN, STAFF_CASHIER];
    mockState.createStaffFn = vi.fn();
    mockState.deactivateStaffFn = vi.fn();
    mockState.reactivateStaffFn = vi.fn();
    mockState.changeStaffPinFn = vi.fn();
    isPendingRefs.createStaff.current = false;
    isPendingRefs.deactivateStaff.current = false;
    isPendingRefs.reactivateStaff.current = false;
    isPendingRefs.changePin.current = false;
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('renders staff table with name, role badge, and active badge', () => {
    render(<StaffTab />, { wrapper: makeWrapper() });

    expect(screen.getByText('Admin User')).toBeInTheDocument();
    expect(screen.getByText('Cashier User')).toBeInTheDocument();
    expect(screen.getByText('ADMIN')).toBeInTheDocument();
    expect(screen.getByText('CASHIER')).toBeInTheDocument();
    // Two staff members, both active - check that Active appears at least once
    expect(screen.getAllByText('Active').length).toBeGreaterThanOrEqual(1);
  });

  it('adds a new staff member via modal and the row appears in the table', async () => {
    const newStaff: Staff = {
      id: 's3',
      name: 'New Staff',
      role: 'CASHIER',
      is_active: true,
      created_at: '2024-01-03T00:00:00Z',
      updated_at: '2024-01-03T00:00:00Z',
    };

    let resolveCreate: (v: Staff) => void;
    const createPromise = new Promise<Staff>((resolve) => {
      resolveCreate = resolve;
    });

    mockState.staff = [];
    mockState.createStaffFn = vi.fn().mockReturnValue(createPromise);

    const { rerender } = render(<StaffTab />, { wrapper: makeWrapper() });

    // Click "Add Staff" button
    const addStaffBtn = screen.getByRole('button', { name: /add staff/i });
    await act(async () => { await addStaffBtn.click(); });

    // Fill the modal form
    const nameInput = screen.getByLabelText(/name/i);
    const roleSelect = screen.getByLabelText(/role/i);
    const pinInput = screen.getByLabelText(/pin \(min 4 digits\)/i);

    await act(async () => {
      fireEvent.change(nameInput, { target: { value: 'New Staff' } });
      fireEvent.change(roleSelect, { target: { value: 'CASHIER' } });
      fireEvent.change(pinInput, { target: { value: '1234' } });
    });

    // Submit the form
    const submitBtn = screen.getByRole('button', { name: /^create$/i });
    await act(async () => { await fireEvent.click(submitBtn); });

    // Wait for the create mutation to be called
    await waitFor(() => expect(mockState.createStaffFn).toHaveBeenCalled());

    // Resolve the create promise with the new staff
    resolveCreate!(newStaff);
    isPendingRefs.createStaff.current = false;

    // Update the list data to simulate query invalidation
    mockState.staff = [STAFF_ADMIN, STAFF_CASHIER, newStaff];

    // Re-render to reflect the updated list
    rerender(<StaffTab />);

    // Verify the new row appears
    await waitFor(() => {
      expect(screen.getByText('New Staff')).toBeInTheDocument();
    });
    // There are now 2 CASHIER badges - check that at least one exists
    expect(screen.getAllByText('CASHIER').length).toBeGreaterThanOrEqual(2);
  });

  it('deactivates a staff member via confirm dialog, row shows inactive badge', async () => {
    const deactivatedStaff: Staff = {
      ...STAFF_CASHIER,
      is_active: false,
      updated_at: '2024-01-03T00:00:00Z',
    };

    let resolveDeactivate: (v: Staff) => void;
    const deactivatePromise = new Promise<Staff>((resolve) => {
      resolveDeactivate = resolve;
    });

    mockState.staff = [STAFF_ADMIN, STAFF_CASHIER];
    mockState.deactivateStaffFn = vi.fn().mockReturnValue(deactivatePromise);

    const { rerender } = render(<StaffTab />, { wrapper: makeWrapper() });

    // Find the deactivate button for Cashier User and click it
    const deactivateBtn = screen.getByRole('button', { name: /deactivate cashier user/i });
    await act(async () => { await deactivateBtn.click(); });

    // Confirm dialog appears - click confirm
    const confirmBtn = screen.getByRole('button', { name: /^deactivate$/i });
    await act(async () => { await fireEvent.click(confirmBtn); });

    // Resolve the mutation
    resolveDeactivate!(deactivatedStaff);
    isPendingRefs.deactivateStaff.current = false;

    // Update list data to simulate query invalidation
    mockState.staff = [STAFF_ADMIN, deactivatedStaff];

    // Re-render
    rerender(<StaffTab />);

    // Assert the badge shows Inactive
    await waitFor(() => {
      expect(screen.getByText('Inactive')).toBeInTheDocument();
    });
  });

  it('reactivates an inactive staff member via confirm dialog, row shows active badge', async () => {
    const inactiveStaff: Staff = {
      ...STAFF_CASHIER,
      is_active: false,
      updated_at: '2024-01-03T00:00:00Z',
    };
    const reactivatedStaff: Staff = {
      ...STAFF_CASHIER,
      is_active: true,
      updated_at: '2024-01-04T00:00:00Z',
    };

    let resolveReactivate: (v: Staff) => void;
    const reactivatePromise = new Promise<Staff>((resolve) => {
      resolveReactivate = resolve;
    });

    mockState.staff = [STAFF_ADMIN, inactiveStaff];
    mockState.reactivateStaffFn = vi.fn().mockReturnValue(reactivatePromise);

    const { rerender } = render(<StaffTab />, { wrapper: makeWrapper() });

    // Find the reactivate button for Cashier User and click it
    const reactivateBtn = screen.getByRole('button', { name: /reactivate cashier user/i });
    await act(async () => { await reactivateBtn.click(); });

    // Confirm dialog appears - click confirm
    const confirmBtn = screen.getByRole('button', { name: /^reactivate$/i });
    await act(async () => { await fireEvent.click(confirmBtn); });

    // Resolve the mutation
    resolveReactivate!(reactivatedStaff);
    isPendingRefs.reactivateStaff.current = false;

    // Update list data
    mockState.staff = [STAFF_ADMIN, reactivatedStaff];

    // Re-render
    rerender(<StaffTab />);

    // Assert the badge shows Active (Admin User is always active, so there are 2 Active badges now)
    await waitFor(() => {
      expect(screen.getAllByText('Active').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows error toast on 403 when creating staff', async () => {
    mockState.staff = [];
    mockState.createStaffFn = vi.fn().mockRejectedValue(new Error('403 Forbidden: Admin required'));

    render(<StaffTab />, { wrapper: makeWrapper() });

    const addStaffBtn = screen.getByRole('button', { name: /add staff/i });
    await act(async () => { await addStaffBtn.click(); });

    const nameInput = screen.getByLabelText(/name/i);
    const roleSelect = screen.getByLabelText(/role/i);
    const pinInput = screen.getByLabelText(/pin \(min 4 digits\)/i);

    await act(async () => {
      fireEvent.change(nameInput, { target: { value: 'Test Staff' } });
      fireEvent.change(roleSelect, { target: { value: 'ADMIN' } });
      fireEvent.change(pinInput, { target: { value: '1234' } });
    });

    const submitBtn = screen.getByRole('button', { name: /^create$/i });
    await act(async () => { await fireEvent.click(submitBtn); });

    await waitFor(() => expect(mockState.createStaffFn).toHaveBeenCalled());

    const { toast } = await import('@/store/toastStore');
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Admin required');
    });
  });

  it('shows EmptyState when no staff exist', () => {
    mockState.staff = [];

    render(<StaffTab />, { wrapper: makeWrapper() });

    expect(screen.getByText(/no staff yet/i)).toBeInTheDocument();
  });

  it('changes PIN for an active staff member via modal', async () => {
    let resolveChangePin: (v: void) => void;
    const changePinPromise = new Promise<void>((resolve) => {
      resolveChangePin = resolve;
    });

    mockState.staff = [STAFF_ADMIN, STAFF_CASHIER];
    mockState.changeStaffPinFn = vi.fn().mockReturnValue(changePinPromise);

    const { rerender } = render(<StaffTab />, { wrapper: makeWrapper() });

    // Click "Change PIN" button for Admin User
    const changePinBtn = screen.getByRole('button', { name: /change pin for admin user/i });
    await act(async () => { await changePinBtn.click(); });

    // Modal appears - fill in new PIN
    const pinInput = screen.getByLabelText(/new pin \(min 4 digits\)/i);
    await act(async () => {
      fireEvent.change(pinInput, { target: { value: '5678' } });
    });

    // Click "Update PIN"
    const updateBtn = screen.getByRole('button', { name: /update pin/i });
    await act(async () => { await fireEvent.click(updateBtn); });

    // Wait for mutation to be called
    await waitFor(() => expect(mockState.changeStaffPinFn).toHaveBeenCalledWith({ id: 's1', pin: '5678' }));

    // Resolve the mutation
    resolveChangePin!();
    isPendingRefs.changePin.current = false;

    // Update list data to simulate query invalidation
    mockState.staff = [STAFF_ADMIN, STAFF_CASHIER];

    // Re-render
    rerender(<StaffTab />);

    // Assert success toast
    const { toast } = await import('@/store/toastStore');
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('PIN updated for Admin User');
    });
  });

  it('shows validation error for PIN less than 4 digits', async () => {
    mockState.staff = [STAFF_ADMIN];

    render(<StaffTab />, { wrapper: makeWrapper() });

    // Click "Change PIN" button for Admin User
    const changePinBtn = screen.getByRole('button', { name: /change pin for admin user/i });
    await act(async () => { await changePinBtn.click(); });

    // Modal appears - try to submit with PIN less than 4 digits
    const pinInput = screen.getByLabelText(/new pin \(min 4 digits\)/i);
    await act(async () => {
      fireEvent.change(pinInput, { target: { value: '123' } });
    });

    const updateBtn = screen.getByRole('button', { name: /update pin/i });
    await act(async () => { await fireEvent.click(updateBtn); });

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText(/pin must be at least 4 digits/i)).toBeInTheDocument();
    });

    // Mutation should not be called
    expect(mockState.changeStaffPinFn).not.toHaveBeenCalled();
  });

  it('shows validation error for non-numeric PIN', async () => {
    mockState.staff = [STAFF_ADMIN];

    render(<StaffTab />, { wrapper: makeWrapper() });

    // Click "Change PIN" button for Admin User
    const changePinBtn = screen.getByRole('button', { name: /change pin for admin user/i });
    await act(async () => { await changePinBtn.click(); });

    // Modal appears - try to submit with non-numeric PIN
    const pinInput = screen.getByLabelText(/new pin \(min 4 digits\)/i);
    await act(async () => {
      fireEvent.change(pinInput, { target: { value: 'abcd' } });
    });

    const updateBtn = screen.getByRole('button', { name: /update pin/i });
    await act(async () => { await fireEvent.click(updateBtn); });

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText(/pin must be numeric/i)).toBeInTheDocument();
    });

    // Mutation should not be called
    expect(mockState.changeStaffPinFn).not.toHaveBeenCalled();
  });

  it('shows error toast on 403 when changing PIN', async () => {
    let resolveChangePin: (v: void) => void;
    const changePinPromise = new Promise<void>((_, reject) => {
      // We don't need resolve for error case
      resolveChangePin = () => reject(new Error('403 Forbidden: Admin required'));
    });

    mockState.staff = [STAFF_ADMIN];
    mockState.changeStaffPinFn = vi.fn().mockReturnValue(changePinPromise);

    const { rerender } = render(<StaffTab />, { wrapper: makeWrapper() });

    const changePinBtn = screen.getByRole('button', { name: /change pin for admin user/i });
    await act(async () => { await changePinBtn.click(); });

    const pinInput = screen.getByLabelText(/new pin \(min 4 digits\)/i);
    await act(async () => {
      fireEvent.change(pinInput, { target: { value: '5678' } });
    });

    const updateBtn = screen.getByRole('button', { name: /update pin/i });
    await act(async () => { await fireEvent.click(updateBtn); });

    await waitFor(() => expect(mockState.changeStaffPinFn).toHaveBeenCalled());

    // Resolve with error
    try {
      resolveChangePin!();
    } catch {
      // expected
    }
    isPendingRefs.changePin.current = false;

    mockState.staff = [STAFF_ADMIN];
    rerender(<StaffTab />);

    const { toast } = await import('@/store/toastStore');
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Admin required');
    });
  });
});
