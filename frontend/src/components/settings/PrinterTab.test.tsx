import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PrinterTab } from './PrinterTab';
import { useAuthStore } from '@/store/authStore';
import type { ReactNode } from 'react';

const SETTINGS: Record<string, string> = {
  printer_type: 'usb',
  printer_usb_vendor: '0x0416',
  printer_usb_product: '0x5011',
};

const mockState = {
  settings: {} as Record<string, string>,
  patchFn: vi.fn(),
};

vi.mock('@/api/settings', () => ({
  useSettings: () => ({
    data: mockState.settings,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useDiscoveredPrinters: () => ({
    data: [],
    isLoading: false,
    refetch: vi.fn(),
  }),
  patchSettings: (patch: Record<string, string>) => mockState.patchFn(patch),
  parsePrinterConfig: (settings: Record<string, string>) => ({
    type: (settings['printer_type'] ?? '') as 'usb' | 'network' | '',
    vendor: settings['printer_usb_vendor'] ?? '',
    product: settings['printer_usb_product'] ?? '',
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

describe('PrinterTab', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'test-token' });
    mockState.settings = SETTINGS;
    mockState.patchFn = vi.fn().mockResolvedValue({});
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('seeds the form from current printer settings', () => {
    render(<PrinterTab />, { wrapper: makeWrapper() });

    // The currently configured section displays the USB vendor/product
    expect(screen.getByText(/VID: 0x0416/)).toBeInTheDocument();
    expect(screen.getByText(/PID: 0x5011/)).toBeInTheDocument();
  });

  it('saves printer config (PATCH with printer keys) and shows success toast', async () => {
    mockState.settings = {
      printer_type: 'network',
      printer_usb_vendor: '0x0416',
      printer_usb_product: '0x5011',
    };
    render(<PrinterTab />, { wrapper: makeWrapper() });

    const typeSelect = screen.getByLabelText(/connection type/i);
    await act(async () => {
      fireEvent.change(typeSelect, { target: { value: 'usb' } });
    });

    const saveBtn = screen.getByRole('button', { name: /^save$/i });
    await act(async () => {
      await fireEvent.click(saveBtn);
    });

    await waitFor(() =>
      expect(mockState.patchFn).toHaveBeenCalledWith({
        printer_type: 'usb',
        printer_usb_vendor: '0x0416',
        printer_usb_product: '0x5011',
      }),
    );

    const { toast } = await import('@/store/toastStore');
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Printer settings saved');
    });
  });
});
