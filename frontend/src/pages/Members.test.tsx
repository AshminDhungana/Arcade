import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { MembersPage } from './Members';
import { useAuthStore } from '@/store/authStore';
import type { Member } from '@/types/members';

const MEMBER: Member = {
  id: 'm1',
  name: 'John',
  phone: '9800000001',
  birth_month: null,
  wallet_balance_paise: 25050,
  loyalty_points: 0,
  tier: 'BRONZE',
  total_visits: 0,
  total_seconds_played: 0,
  created_at: '',
  updated_at: '',
};

vi.mock('@/api/members', () => ({
  useMembers: () => ({ data: [MEMBER], isLoading: false, isError: false, refetch: vi.fn() }),
  useCreateMember: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useTopupWallet: () => ({ mutateAsync: vi.fn(), isPending: false }),
  usePackages: () => ({ data: [] }),
  usePurchasePackage: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useMemberSessions: () => ({ data: [] }),
  useWalletTransactions: () => ({ data: [] }),
}));

vi.mock('@/components/MemberSearch', () => ({
  MemberSearch: ({ onSelect }: { onSelect: (m: Member) => void }) => (
    <button type="button" onClick={() => onSelect(MEMBER)}>search</button>
  ),
}));

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe('MembersPage', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'tok' });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('lists members and shows formatted wallet balance', () => {
    render(<MembersPage />, { wrapper: makeWrapper() });
    expect(screen.getByText('John')).toBeInTheDocument();
    expect(screen.getByText('Rs. 250.50')).toBeInTheDocument();
  });
});
