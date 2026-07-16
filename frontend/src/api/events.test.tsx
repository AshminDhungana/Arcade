import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  fetchEvents, useEvents, createEvent, recordMatchResult,
} from './events';
import { useAuthStore } from '@/store/authStore';

const EVENTS = [
  { id: 'e1', name: 'FIFA Cup', game_title: 'FIFA', event_date: '2026-08-01T10:00:00Z',
    entry_fee_paise: 5000, prize_pool_paise: 20000, bracket_type: 'SINGLE_ELIMINATION', status: 'UPCOMING' },
];

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) =>
    <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('events API', () => {
  beforeEach(() => { useAuthStore.setState({ accessToken: 'tok' }); });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('fetchEvents hits /api/events with Bearer header', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify(EVENTS), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);
    const data = await fetchEvents('tok');
    expect(fetchMock).toHaveBeenCalledWith('/api/events', {
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer tok' },
    });
    expect(data).toEqual(EVENTS);
  });

  it('useEvents exposes the list', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(EVENTS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    const { result } = renderHook(() => useEvents(), { wrapper: makeWrapper() });
    await waitFor(() => expect(result.current.data).toBeDefined());
    expect(result.current.data?.[0].name).toBe('FIFA Cup');
  });

  it('createEvent POSTs to /api/events', async () => {
    const fetchMock = vi.fn(async (url: string, opts?: RequestInit) => {
      expect(url).toBe('/api/events');
      expect(opts?.method).toBe('POST');
      expect(JSON.parse(opts?.body as string)).toMatchObject({ name: 'Smash' });
      return new Response(JSON.stringify({ id: 'e2', name: 'Smash' }), { status: 201, headers: { 'Content-Type': 'application/json' } });
    });
    vi.stubGlobal('fetch', fetchMock);
    const res = await createEvent({ name: 'Smash', game_title: 'Smash', event_date: '2026-08-02T10:00:00Z' }, 'tok');
    expect(res.id).toBe('e2');
  });

  it('recordMatchResult PATCHes /api/events/:id/match', async () => {
    const fetchMock = vi.fn(async (url: string, opts?: RequestInit) => {
      expect(url).toBe('/api/events/e1/match');
      expect(opts?.method).toBe('PATCH');
      expect(JSON.parse(opts?.body as string)).toEqual({ match_id: 'm1', winner_id: 'pA' });
      return new Response(JSON.stringify({ id: 'm1' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
    vi.stubGlobal('fetch', fetchMock);
    await recordMatchResult('e1', { match_id: 'm1', winner_id: 'pA' }, 'tok');
  });
});
