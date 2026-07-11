import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { PricingTab } from './PricingTab';
import { useAuthStore } from '@/store/authStore';
import type { Zone, DeviceType } from '@/types/settings';
import { formatPaise } from '@/hooks/useFormatPaise';

const ZONE: Zone = {
  id: 'zone1',
  name: 'VIP Zone',
  rate_per_minute_paise: 150,
  rate_per_hour_paise: 6000,
  pricing_model: 'PER_MINUTE',
  block_minutes: null,
};

const DEVICE_TYPE: DeviceType = {
  id: 'dt1',
  name: 'PC',
  description: 'Gaming PC',
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
  zones: [] as Zone[],
  deviceTypes: [] as DeviceType[],
  createZoneFn: vi.fn(),
  updateZoneFn: vi.fn(),
  deleteZoneFn: vi.fn(),
  createDeviceTypeFn: vi.fn(),
  updateDeviceTypeFn: vi.fn(),
  deleteDeviceTypeFn: vi.fn(),
};

// Mock modules at top level (hoisted)
vi.mock('@/api/settings', () => ({
  useZones: () => ({
    data: mockState.zones,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreateZone: () => ({
    mutateAsync: mockState.createZoneFn,
    isPending: false,
  }),
  useUpdateZone: () => ({
    mutateAsync: mockState.updateZoneFn,
    isPending: false,
  }),
  useDeleteZone: () => ({
    mutateAsync: mockState.deleteZoneFn,
    isPending: false,
  }),
  useDeviceTypes: () => ({
    data: mockState.deviceTypes,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useCreateDeviceType: () => ({
    mutateAsync: mockState.createDeviceTypeFn,
    isPending: false,
  }),
  useUpdateDeviceType: () => ({
    mutateAsync: mockState.updateDeviceTypeFn,
    isPending: false,
  }),
  useDeleteDeviceType: () => ({
    mutateAsync: mockState.deleteDeviceTypeFn,
    isPending: false,
  }),
}));

vi.mock('@/store/toastStore', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('PricingTab', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'test-token' });
    mockState.zones = [];
    mockState.deviceTypes = [];
    mockState.createZoneFn = vi.fn().mockResolvedValue(undefined);
    mockState.updateZoneFn = vi.fn().mockResolvedValue(undefined);
    mockState.deleteZoneFn = vi.fn().mockResolvedValue(undefined);
    mockState.createDeviceTypeFn = vi.fn().mockResolvedValue(undefined);
    mockState.updateDeviceTypeFn = vi.fn().mockResolvedValue(undefined);
    mockState.deleteDeviceTypeFn = vi.fn().mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty zones and device types initially', () => {
    render(<PricingTab />, { wrapper: makeWrapper() });

    expect(screen.getByText('No zones configured. Add one to get started.')).toBeInTheDocument();
    expect(screen.getByText('No device types yet. Add one to get started.')).toBeInTheDocument();
  });

  it('lists zones with rates formatted as rupees via formatPaise', () => {
    mockState.zones = [ZONE];
    mockState.deviceTypes = [DEVICE_TYPE];

    render(<PricingTab />, { wrapper: makeWrapper() });

    expect(screen.getByText('VIP Zone')).toBeInTheDocument();
    expect(screen.getByText(formatPaise(150))).toBeInTheDocument(); // rate/min
    expect(screen.getByText(formatPaise(6000))).toBeInTheDocument(); // rate/hr
    expect(screen.getByText('Per Minute')).toBeInTheDocument(); // pricing model badge
    expect(screen.getByText('PC')).toBeInTheDocument();
  });

  it('adds a zone with rate_per_hour_paise shown as rupees; list updates', async () => {
    const newZone: Zone = {
      id: 'zone2',
      name: 'Standard Zone',
      rate_per_minute_paise: 100,
      rate_per_hour_paise: 5000,
      pricing_model: 'PER_MINUTE',
      block_minutes: null,
    };

    let resolveCreate: (v: Zone) => void;
    const createPromise = new Promise<Zone>((resolve) => {
      resolveCreate = resolve;
    });

    mockState.zones = [];
    mockState.deviceTypes = [];
    mockState.createZoneFn = vi.fn().mockReturnValue(createPromise);

    const { rerender } = render(<PricingTab />, { wrapper: makeWrapper() });

    // Click "Add Zone" button
    const addZoneBtn = screen.getByRole('button', { name: /add zone/i });
    await addZoneBtn.click();

    // Fill the modal form
    const nameInput = screen.getByLabelText(/zone name/i);
    const rateMinInput = screen.getByLabelText(/rate per minute \(₹\)/i);
    const rateHrInput = screen.getByLabelText(/rate per hour \(₹\)/i);
    const pricingModelSelect = screen.getByLabelText(/pricing model/i);

    fireEvent.change(nameInput, { target: { value: 'Standard Zone' } });
    fireEvent.change(rateMinInput, { target: { value: '1' } });
    fireEvent.change(rateHrInput, { target: { value: '50' } });
    fireEvent.change(pricingModelSelect, { target: { value: 'PER_MINUTE' } });

    // Submit
    const submitBtn = screen.getByRole('button', { name: /^create$/i });
    await fireEvent.click(submitBtn);

    // Resolve the create mutation with the new zone
    resolveCreate!(newZone);

    // Update zones data and re-render (simulating query invalidation)
    mockState.zones = [newZone];
    rerender(<PricingTab />);

    // Wait for list to update
    await waitFor(() => {
      expect(screen.getByText('Standard Zone')).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByText(formatPaise(100))).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByText(formatPaise(5000))).toBeInTheDocument();
    });
  });
});
