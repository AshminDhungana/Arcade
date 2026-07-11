import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { SchedulesTab } from './SchedulesTab';
import { useAuthStore } from '@/store/authStore';
import type { PeakSchedule } from '@/types/settings';
import { formatPaise } from '@/hooks/useFormatPaise';

const SCHEDULE: PeakSchedule = {
  id: 'sched1',
  name: 'Weekend Peak',
  is_peak: true,
  day_of_week: 0, // Sunday
  start_time: '18:00',
  end_time: '23:59',
  surcharge_paise: 5000, // Rs. 50.00/hour
};


function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

// Hoisted mock state
const mockState = {
  schedules: [] as PeakSchedule[],
  createScheduleFn: vi.fn(),
  updateScheduleFn: vi.fn(),
  deleteScheduleFn: vi.fn(),
};

// Mock the settings API hooks
vi.mock('@/api/settings', () => ({
  useSchedules: () => ({
    data: mockState.schedules,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreateSchedule: () => ({
    mutateAsync: mockState.createScheduleFn,
    isPending: false,
  }),
  useUpdateSchedule: () => ({
    mutateAsync: mockState.updateScheduleFn,
    isPending: false,
  }),
  useDeleteSchedule: () => ({
    mutateAsync: mockState.deleteScheduleFn,
    isPending: false,
  }),
}));

// Mock toast
vi.mock('@/store/toastStore', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('SchedulesTab', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'test-token' });
    mockState.schedules = [];
    mockState.createScheduleFn = vi.fn().mockResolvedValue(undefined);
    mockState.updateScheduleFn = vi.fn().mockResolvedValue(undefined);
    mockState.deleteScheduleFn = vi.fn().mockResolvedValue(undefined);
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('renders empty state when no schedules exist', () => {
    render(<SchedulesTab />, { wrapper: makeWrapper() });

    expect(screen.getByText('No schedules configured. Add one to get started.')).toBeInTheDocument();
  });

  it('lists schedules with peak/off-peak badge, days, time window, and formatted surcharge', () => {
    mockState.schedules = [SCHEDULE];

    render(<SchedulesTab />, { wrapper: makeWrapper() });

    expect(screen.getByText('Weekend Peak')).toBeInTheDocument();
    // Peak badge
    expect(screen.getByText('Peak')).toBeInTheDocument();
    // Days - Sunday
    expect(screen.getByText('Sunday')).toBeInTheDocument();
    // Time window
    expect(screen.getByText('18:00–23:59')).toBeInTheDocument();
    // Surcharge formatted as rupees
    expect(screen.getByText(formatPaise(5000))).toBeInTheDocument(); // Rs. 50.00
  });

  it('adds a schedule with is_peak=false (Off-Peak), all days, and surcharge in rupees converted to paise; list updates', async () => {
    const newSchedule: PeakSchedule = {
      id: 'sched2',
      name: 'Weekday Off-Peak',
      is_peak: false,
      day_of_week: null, // All days
      start_time: '08:00',
      end_time: '18:00',
      surcharge_paise: 1000, // Rs. 10.00/hour
    };

    let resolveCreate: (v: PeakSchedule) => void;
    const createPromise = new Promise<PeakSchedule>((resolve) => {
      resolveCreate = resolve;
    });

    mockState.schedules = [];
    mockState.createScheduleFn = vi.fn().mockReturnValue(createPromise);

    const { rerender } = render(<SchedulesTab />, { wrapper: makeWrapper() });

    // Click "Add Schedule" button
    const addBtn = screen.getByRole('button', { name: /add schedule/i });
    await addBtn.click();

    // Fill the modal form
    const nameInput = screen.getByLabelText(/schedule name/i);
    const daySelect = screen.getByLabelText(/day of week/i);
    const startTimeInput = screen.getByLabelText(/start time \(hh:mm\)/i);
    const endTimeInput = screen.getByLabelText(/end time \(hh:mm\)/i);
    const surchargeInput = screen.getByLabelText(/surcharge per hour \(₹\)/i);

    fireEvent.change(nameInput, { target: { value: 'Weekday Off-Peak' } });
    // It's off-peak, so don't toggle the switch (default false)
    fireEvent.change(daySelect, { target: { value: 'all' } });
    fireEvent.change(startTimeInput, { target: { value: '08:00' } });
    fireEvent.change(endTimeInput, { target: { value: '18:00' } });
    fireEvent.change(surchargeInput, { target: { value: '10' } });

    // Submit the form
    const submitBtn = screen.getByRole('button', { name: /create/i });
    fireEvent.click(submitBtn);

    // Resolve the create promise with the new schedule
    await waitFor(() => expect(mockState.createScheduleFn).toHaveBeenCalled());
    const createCall = mockState.createScheduleFn.mock.calls[0][0];
    expect(createCall).toEqual({
      name: 'Weekday Off-Peak',
      is_peak: false,
      day_of_week: null,
      start_time: '08:00',
      end_time: '18:00',
      surcharge_paise: 1000,
    });

    resolveCreate!(newSchedule);
    await waitFor(() => {
      mockState.schedules = [newSchedule];
      rerender(<SchedulesTab />);
    });

    // Verify the new schedule appears in the list
    expect(screen.getByText('Weekday Off-Peak')).toBeInTheDocument();
    expect(screen.getByText('Off-Peak')).toBeInTheDocument();
    expect(screen.getByText('All days')).toBeInTheDocument();
    expect(screen.getByText('08:00–18:00')).toBeInTheDocument();
    expect(screen.getByText(formatPaise(1000))).toBeInTheDocument(); // Rs. 10.00
  });

  it('shows error toast on 403 when creating schedule', async () => {
    mockState.schedules = [];
    mockState.createScheduleFn = vi.fn().mockRejectedValue(new Error('403 Forbidden: Admin required'));

    render(<SchedulesTab />, { wrapper: makeWrapper() });

    const addBtn = screen.getByRole('button', { name: /add schedule/i });
    await addBtn.click();

    const nameInput = screen.getByLabelText(/schedule name/i);
    const startTimeInput = screen.getByLabelText(/start time \(hh:mm\)/i);
    const endTimeInput = screen.getByLabelText(/end time \(hh:mm\)/i);
    const surchargeInput = screen.getByLabelText(/surcharge per hour \(₹\)/i);

    fireEvent.change(nameInput, { target: { value: 'Test' } });
    fireEvent.change(startTimeInput, { target: { value: '10:00' } });
    fireEvent.change(endTimeInput, { target: { value: '12:00' } });
    fireEvent.change(surchargeInput, { target: { value: '10' } });

    const submitBtn = screen.getByRole('button', { name: /create/i });
    fireEvent.click(submitBtn);

    await waitFor(() => expect(mockState.createScheduleFn).toHaveBeenCalled());

    // Should show error toast
    const { toast } = await import('@/store/toastStore');
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Admin required');
    });
  });
});
