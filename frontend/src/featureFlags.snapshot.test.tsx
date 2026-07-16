import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { NavShell } from './components/NavShell';
import { useFeatureFlagStore } from './store/featureFlagStore';
import type { FeatureFlags } from './store/featureFlagStore';

const KEYS = [
  'enable_members', 'enable_packages', 'enable_pos', 'enable_inventory',
  'enable_reservations', 'enable_vouchers', 'enable_tournaments',
  'enable_expense_tracking', 'enable_health_monitoring', 'require_member_for_session',
] as const;

const ALL_OFF = Object.fromEntries(KEYS.map((k) => [k, false])) as Record<string, boolean>;
const ALL_ON = Object.fromEntries(KEYS.map((k) => [k, true])) as Record<string, boolean>;

const renderNav = (flags: Record<string, boolean>) => {
  useFeatureFlagStore.getState().setFlags(flags as unknown as FeatureFlags);
  return render(<MemoryRouter><NavShell><div>child</div></NavShell></MemoryRouter>);
};

describe('feature flag matrix', () => {
  beforeEach(() => useFeatureFlagStore.getState().clear());

  it('all OFF: only Dashboard/Analytics/Settings nav visible', () => {
    renderNav(ALL_OFF);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
    expect(screen.queryByText('Members')).not.toBeInTheDocument();
    expect(screen.queryByText('Events')).not.toBeInTheDocument();
  });

  it('all ON: Members and Events nav visible', () => {
    renderNav(ALL_ON);
    expect(screen.getByText('Members')).toBeInTheDocument();
    expect(screen.getByText('Events')).toBeInTheDocument();
  });

  it.each(KEYS)('toggling %s alone does not break the nav shell', (key) => {
    renderNav({ ...ALL_OFF, [key]: true });
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });
});
