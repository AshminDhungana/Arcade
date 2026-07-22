import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemberDetailDrawer } from './MemberDetailDrawer';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import type { Member, Package, WalletTransaction } from '@/types/members';
import type { SessionResponse } from '@/types/session';
import type { MemberTab } from './Members';

const ALL_FLAGS = {
  enable_members: false, enable_packages: false, enable_pos: false,
  enable_inventory: false, enable_reservations: false, enable_vouchers: false,
  enable_tournaments: false, enable_expense_tracking: false,
  enable_health_monitoring: false, require_member_for_session: false,
  require_print_before_release: false, enable_assigned_time_limit: false,
};

const MEMBER: Member = {
  id: 'm1', name: 'Test Member', phone: '9800000000', birth_month: 5,
  wallet_balance_paise: 0, loyalty_points: 0, tier: 'BRONZE', total_visits: 0,
  total_seconds_played: 0, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
};

const EMPTY_PACKAGES: Package[] = [];
const EMPTY_SESSIONS: SessionResponse[] = [];
const EMPTY_TX: WalletTransaction[] = [];

const noop = () => Promise.resolve();

function renderDrawer(activeTab: MemberTab = 'sessions') {
  return render(
    <MemberDetailDrawer
      open
      onClose={() => {}}
      member={MEMBER}
      activeTab={activeTab}
      onTabChange={() => {}}
      packages={EMPTY_PACKAGES}
      sessions={EMPTY_SESSIONS}
      walletTransactions={EMPTY_TX}
      onTopup={noop}
      onPurchasePackage={noop}
      isTopupPending={false}
      isPurchasePending={false}
    />,
  );
}

describe('MemberDetailDrawer Packages tab gating', () => {
  beforeEach(() => {
    useFeatureFlagStore.getState().clear();
  });

  it('hides the Packages tab when enable_packages is off', () => {
    useFeatureFlagStore.getState().setFlags({ ...ALL_FLAGS, enable_packages: false });
    renderDrawer();
    expect(screen.queryByRole('tab', { name: /packages/i })).not.toBeInTheDocument();
  });

  it('shows the Packages tab when enable_packages is on', () => {
    useFeatureFlagStore.getState().setFlags({ ...ALL_FLAGS, enable_packages: true });
    renderDrawer();
    expect(screen.getByRole('tab', { name: /packages/i })).toBeInTheDocument();
  });
});
