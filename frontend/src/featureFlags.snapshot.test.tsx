import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { NavShell } from './components/NavShell';
import { useFeatureFlagStore } from './store/featureFlagStore';
import type { FeatureFlags } from '@/types/pos';

const KEYS = [
  'enable_members', 'enable_packages', 'enable_pos', 'enable_inventory',
  'enable_reservations', 'enable_vouchers', 'enable_tournaments',
  'enable_expense_tracking', 'enable_health_monitoring',
  'require_member_for_session',
  'require_print_before_release',
  'enable_assigned_time_limit',
] as const;

const ALL_OFF = Object.fromEntries(KEYS.map((k) => [k, false])) as unknown as FeatureFlags;
const ALL_ON = Object.fromEntries(KEYS.map((k) => [k, true])) as unknown as FeatureFlags;

const renderNav = (flags: FeatureFlags) => {
  useFeatureFlagStore.getState().setFlags(flags);
  return render(
    <MemoryRouter>
      <NavShell>
        <div>child</div>
      </NavShell>
    </MemoryRouter>,
  );
};

describe('feature flag snapshot matrix', () => {
  beforeEach(() => useFeatureFlagStore.getState().clear());

  it('all flags OFF', () => {
    const { asFragment } = renderNav(ALL_OFF);
    expect(asFragment()).toMatchSnapshot();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.queryByText('Members')).not.toBeInTheDocument();
    expect(screen.queryByText('Events')).not.toBeInTheDocument();
  });

  it('all flags ON', () => {
    const { asFragment } = renderNav(ALL_ON);
    expect(asFragment()).toMatchSnapshot();
    expect(screen.getByText('Members')).toBeInTheDocument();
    expect(screen.getByText('Events')).toBeInTheDocument();
  });

  it.each(KEYS)('only %s enabled', (key) => {
    const flags = { ...ALL_OFF } as Record<string, boolean>;
    flags[key] = true;
    const { asFragment } = renderNav(flags as unknown as FeatureFlags);
    expect(asFragment()).toMatchSnapshot();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });
});
