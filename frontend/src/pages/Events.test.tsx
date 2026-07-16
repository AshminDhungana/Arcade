import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { EventsPage } from './Events';
import { useAuthStore } from '@/store/authStore';

const EVENTS = [
  { id: 'e1', name: 'FIFA Cup', game_title: 'FIFA 24', event_date: '2026-08-01T10:00:00Z',
    entry_fee_paise: 5000, prize_pool_paise: 20000, bracket_type: 'SINGLE_ELIMINATION', status: 'UPCOMING' },
];

const SUMMARY = {
  event: EVENTS[0],
  participant_count: 2,
  participants: [
    { id: 'pA', event_id: 'e1', member_id: null, name: 'Alice', seat_id: null, bracket_position: 0, eliminated: false },
    { id: 'pB', event_id: 'e1', member_id: null, name: 'Bob', seat_id: null, bracket_position: 1, eliminated: true },
  ],
  match_count: 1, completed_match_count: 1,
  prize_pool_paise: 20000, entry_fee_paise: 5000, entry_fee_revenue_paise: 10000,
  champion_participant_id: 'pA', is_complete: true,
  matches: [{ id: 'm1', event_id: 'e1', bracket_group: 'WINNERS', round: 1, slot_a_id: 'pA', slot_b_id: 'pB', winner_id: 'pA', status: 'COMPLETED', next_match_id: null, next_loser_match_id: null }],
};

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) =>
    <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('EventsPage', () => {
  beforeEach(() => { useAuthStore.setState({ accessToken: 'tok', staff: { id: 's1', name: 'A', role: 'ADMIN', is_active: true } }); });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('renders the event list and collapses to a single column on mobile', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify(EVENTS), { status: 200, headers: { 'Content-Type': 'application/json' } })));
    const { container } = render(<EventsPage />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('FIFA Cup')).toBeInTheDocument());
    expect(screen.getByText('Rs. 200.00')).toBeInTheDocument(); // prize pool via formatPaise
    expect(container.querySelector('[class*="grid-cols-1"]')).not.toBeNull();
  });

  it('opens the create modal and POSTs a new event (rupees -> paise)', async () => {
    const fetchMock = vi.fn(async (url: string, opts?: RequestInit) => {
      if (url === '/api/events' && opts?.method === 'POST') {
        const body = JSON.parse(opts.body as string);
        expect(body.entry_fee_paise).toBe(1000); // 10.00 -> 1000 paise
        expect(body.bracket_type).toBe('SINGLE_ELIMINATION');
        return new Response(JSON.stringify({ id: 'e2', ...body }), { status: 201, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response(JSON.stringify(EVENTS), { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<EventsPage />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('FIFA Cup')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /new event/i }));
    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Smash' } });
    fireEvent.change(screen.getByLabelText(/game/i), { target: { value: 'Smash' } });
    fireEvent.change(screen.getByLabelText(/entry fee/i), { target: { value: '10' } });
    fireEvent.click(screen.getByRole('button', { name: /create/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/events', expect.objectContaining({ method: 'POST' })));
  });

  it('renders the summary panel with prize pool and champion for a selected event', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      const body = url.includes('/summary') ? SUMMARY : EVENTS;
      return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }));
    render(<EventsPage />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('FIFA Cup')).toBeInTheDocument());
    fireEvent.click(screen.getByLabelText(/open event fifa cup/i));
    await waitFor(() => expect(screen.getByText('Summary')).toBeInTheDocument());
    expect(screen.getByText('Rs. 200.00')).toBeInTheDocument(); // prize pool KPI
    expect(screen.getByText('Alice')).toBeInTheDocument(); // champion
  });
});
