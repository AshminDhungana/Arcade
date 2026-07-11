import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import {
  useZones,
  useCreateZone,
  useDeviceTypes,
  useSchedules,
  useStaff,
  useMenuItems,
} from './settings';
import { useAuthStore } from '@/store/authStore';

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
);

const ZONE = {
  id: 'z1',
  name: 'Zone A',
  rate_per_minute_paise: 5,
  rate_per_hour_paise: 300,
  pricing_model: 'PER_MINUTE' as const,
  block_minutes: null,
};

beforeEach(() => {
  useAuthStore.setState({ accessToken: 'tok' });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('settings API client', () => {
  it('useZones fetches GET /api/zones', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [ZONE] });
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useZones(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith('/api/zones', expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer tok' }),
    }));
    expect(result.current.data?.[0].id).toBe('z1');
  });

  it('useCreateZone POSTs and invalidates zones', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ZONE });
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useCreateZone(), { wrapper });
    result.current.mutate(ZONE);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/zones');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body as string)).toMatchObject({ name: 'Zone A' });
  });

  it('useDeviceTypes fetches GET /api/device-types', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ id: 'd1', name: 'PC', description: null }],
    });
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useDeviceTypes(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith('/api/device-types', expect.anything());
  });

  it('useSchedules fetches GET /api/schedules', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useSchedules(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith('/api/schedules', expect.anything());
  });

  it('useStaff fetches GET /api/staff', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [{ id: 's1', name: 'Alice', role: 'CASHIER', is_active: true }],
    });
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useStaff(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith('/api/staff', expect.anything());
  });

  it('useMenuItems fetches GET /api/menu-items', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal('fetch', fetchMock);
    const { result } = renderHook(() => useMenuItems(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(fetchMock).toHaveBeenCalledWith('/api/menu-items', expect.anything());
  });
});
