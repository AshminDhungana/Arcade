import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';
import { EventsWidget } from './EventsWidget';
import { useAuthStore } from '@/store/authStore';

const EVENTS = [
  { id: 'e1', name: 'FIFA Cup', game_title: 'FIFA 24', event_date: '2026-08-15T18:00:00Z', entry_fee_paise: 5000, prize_pool_paise: 20000, bracket_type: 'SINGLE_ELIMINATION', status: 'UPCOMING' },
  { id: 'e2', name: 'Tekken Tournament', game_title: 'Tekken 8', event_date: '2026-08-20T19:00:00Z', entry_fee_paise: 3000, prize_pool_paise: 10000, bracket_type: 'DOUBLE_ELIMINATION', status: 'UPCOMING' },
  { id: 'e3', name: 'Past Event', game_title: 'Street Fighter', event_date: '2026-07-01T18:00:00Z', entry_fee_paise: 2000, prize_pool_paise: 5000, bracket_type: 'SINGLE_ELIMINATION', status: 'COMPLETED' },
];

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/']}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('EventsWidget', () => {
  beforeEach(() => { useAuthStore.setState({ accessToken: 'tok' }); });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('renders upcoming events sorted by date', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(EVENTS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    render(<EventsWidget />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('Upcoming Events')).toBeInTheDocument());
    // Wait for event data to load
    await waitFor(() => expect(screen.getByText('FIFA Cup')).toBeInTheDocument());
    expect(screen.getByText('Tekken Tournament')).toBeInTheDocument();
    expect(screen.queryByText('Past Event')).not.toBeInTheDocument();
    // FIFA Cup should appear first (earlier date)
    const fifaEl = screen.getByText('FIFA Cup');
    const tekkenEl = screen.getByText('Tekken Tournament');
    expect(fifaEl.compareDocumentPosition(tekkenEl) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('shows entry fee and prize pool per event', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(EVENTS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    render(<EventsWidget />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('FIFA Cup')).toBeInTheDocument());
    // Entry fee rendered as ₹50, prize pool as Rs. 200.00
    expect(screen.getByText('₹50')).toBeInTheDocument(); // entry fee
    expect(screen.getByText('Rs. 200.00')).toBeInTheDocument(); // prize pool
  });

  it('shows empty state when no upcoming events', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify([EVENTS[2]]), { status: 200, headers: { 'Content-Type': 'application/json' } }))); // only completed
    render(<EventsWidget />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText(/no upcoming events/i)).toBeInTheDocument());
  });

  it('View All link navigates to /events', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(EVENTS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    render(<EventsWidget />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByRole('link', { name: /view all/i })).toBeInTheDocument());
    expect(screen.getByRole('link', { name: /view all/i })).toHaveAttribute('href', '/events');
  });
});
