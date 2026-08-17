import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { RegisterParticipantModal } from './RegisterParticipantModal';
import { useAuthStore } from '@/store/authStore';
import { useRegisterParticipant } from '@/api/events';
import { useActiveMembers } from '@/api/members';
import { useAvailableSeats } from '@/api/seats';
import { toast } from '@/store/toastStore';

const MEMBERS = [
  { id: 'm1', name: 'Alice', phone: '9800000001', wallet_balance_paise: 5000, tier: 'BRONZE', is_active: true },
  { id: 'm2', name: 'Bob', phone: '9800000002', wallet_balance_paise: 3000, tier: 'SILVER', is_active: true },
];

const SEATS = [
  { id: 's1', name: 'Seat 1', zone_id: 'z1', status: 'AVAILABLE', updated_at: '2026-01-01T00:00:00Z' },
  { id: 's2', name: 'Seat 2', zone_id: 'z1', status: 'ONLINE', updated_at: '2026-01-01T00:00:00Z' },
];

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('RegisterParticipantModal', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'tok', staff: { id: 's1', name: 'A', role: 'ADMIN', is_active: true } });
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/members')) return new Response(JSON.stringify(MEMBERS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/seats')) return new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      return new Response(JSON.stringify({ id: 'p1' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }));
    vi.spyOn(toast, 'error').mockImplementation(() => {});
    vi.spyOn(toast, 'success').mockImplementation(() => {});
  });
  afterEach(() => { vi.unstubAllGlobals(); vi.clearAllMocks(); });

  it('renders member mode by default with member dropdown and wallet preview after selection', async () => {
    render(<RegisterParticipantModal open={true} eventId="e1" onClose={vi.fn()} entryFeePaise={3000} />, { wrapper: makeWrapper() });
    await waitFor(() => expect(screen.getByText('Register participant')).toBeInTheDocument());
    expect(screen.getByRole('radio', { name: /member/i })).toBeChecked();
    // Wait for member data to load - select has data-testid
    await waitFor(() => expect(screen.getByTestId('member-select')).toBeInTheDocument());
    // Wallet preview only appears after member selection - select a member first
    await userEvent.selectOptions(screen.getByTestId('member-select'), 'm1');
    // Now wallet preview should appear
    await waitFor(() => expect(screen.getByText(/wallet balance/i)).toBeInTheDocument());
  });

  it('switches to walk-in mode showing name input', async () => {
    render(<RegisterParticipantModal open={true} eventId="e1" onClose={vi.fn()} />, { wrapper: makeWrapper() });
    await userEvent.click(screen.getByRole('radio', { name: /walk.in/i }));
    expect(screen.getByRole('radio', { name: /walk.in/i })).toBeChecked();
    // Input component renders label + input, use getByPlaceholderText
    expect(screen.getByPlaceholderText(/enter name/i)).toBeInTheDocument();
    // Member dropdown should be gone (the select element)
    expect(screen.queryByTestId('member-select')).not.toBeInTheDocument();
  });

  it('member mode: submits member_id and seat_id', async () => {
    const fetchMock = vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes('/members')) return new Response(JSON.stringify(MEMBERS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/seats')) return new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/events/e1/register')) {
        expect(JSON.parse(opts?.body as string)).toMatchObject({ member_id: 'm1', seat_id: 's1' });
        return new Response(JSON.stringify({ id: 'e1' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response('', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<RegisterParticipantModal open={true} eventId="e1" onClose={vi.fn()} entryFeePaise={3000} />, { wrapper: makeWrapper() });
    // Wait for member and seat data to load (select not disabled)
    await waitFor(() => expect(screen.getByTestId('member-select')).not.toBeDisabled());
    await waitFor(() => expect(screen.getByTestId('seat-select')).toBeInTheDocument());
    await userEvent.selectOptions(screen.getByTestId('member-select'), 'm1');
    await userEvent.selectOptions(screen.getByTestId('seat-select'), 's1');
    await userEvent.click(screen.getByRole('button', { name: /register/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/events/e1/register', expect.objectContaining({ method: 'POST' })));
  });

  it('walk-in mode: submits name and optional seat_id', async () => {
    const fetchMock = vi.fn(async (url: string, opts?: RequestInit) => {
      if (url.includes('/members')) return new Response(JSON.stringify(MEMBERS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/seats')) return new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/events/e1/register')) {
        expect(JSON.parse(opts?.body as string)).toMatchObject({ name: 'Walk-in Will', seat_id: 's2' });
        return new Response(JSON.stringify({ id: 'e1' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response('', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<RegisterParticipantModal open={true} eventId="e1" onClose={vi.fn()} />, { wrapper: makeWrapper() });
    await userEvent.click(screen.getByRole('radio', { name: /walk.in/i }));
    await userEvent.type(screen.getByPlaceholderText(/enter name/i), 'Walk-in Will');
    // Wait for seat data to load
    await waitFor(() => expect(screen.getByTestId('seat-select')).toBeInTheDocument());
    await userEvent.selectOptions(screen.getByTestId('seat-select'), 's2');
    await userEvent.click(screen.getByRole('button', { name: /register/i }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/events/e1/register', expect.objectContaining({ method: 'POST' })));
  });

  it('shows error toast on registration failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/members')) return new Response(JSON.stringify(MEMBERS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      if (url.includes('/seats')) return new Response(JSON.stringify(SEATS), { status: 200, headers: { 'Content-Type': 'application/json' } });
      return new Response('', { status: 500 });
    }));

    render(<RegisterParticipantModal open={true} eventId="e1" onClose={vi.fn()} entryFeePaise={3000} />, { wrapper: makeWrapper() });
    // Wait for member data to load (select not disabled)
    await waitFor(() => expect(screen.getByTestId('member-select')).not.toBeDisabled());
    // Select a member first to pass validation
    await userEvent.selectOptions(screen.getByTestId('member-select'), 'm1');
    await userEvent.click(screen.getByRole('button', { name: /register/i }));
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Failed to register participant'));
  });
});
