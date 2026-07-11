import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { MemberSearch } from './MemberSearch';
import { useAuthStore } from '@/store/authStore';
import type { Member } from '@/types/members';

const SAMPLE: Member[] = [
  { id: 'm1', name: 'John', phone: '9800000001', birth_month: null, wallet_balance_paise: 0, loyalty_points: 0, tier: 'BRONZE', total_visits: 0, total_seconds_played: 0, created_at: '', updated_at: '' },
  { id: 'm2', name: 'Jane', phone: '9800000002', birth_month: null, wallet_balance_paise: 0, loyalty_points: 0, tier: 'BRONZE', total_visits: 0, total_seconds_played: 0, created_at: '', updated_at: '' },
];

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe('MemberSearch', () => {
  let fetchMock: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    fetchMock = vi.fn(
      async () =>
        new Response(JSON.stringify(SAMPLE), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
    );
    vi.stubGlobal('fetch', fetchMock);
    useAuthStore.setState({ accessToken: 'tok' });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('debounces input, shows a matching member, and selects on click', async () => {
    const onSelect = vi.fn();
    render(<MemberSearch onSelect={onSelect} />, { wrapper: makeWrapper() });
    const input = screen.getByPlaceholderText(/Search members/i);
    fireEvent.change(input, { target: { value: 'jo' } });
    await waitFor(() => expect(screen.getByText('John')).toBeInTheDocument(), {
      timeout: 3000,
    });
    fireEvent.click(screen.getByText('John'));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'm1', name: 'John' }),
    );
  });
});
