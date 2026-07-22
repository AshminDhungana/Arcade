import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { NavShell } from './NavShell';
import { useFeatureFlagStore } from '@/store/featureFlagStore';

const BASE = {
  enable_members: false, enable_packages: false, enable_pos: false,
  enable_inventory: false, enable_reservations: false, enable_vouchers: false,
  enable_tournaments: false, enable_expense_tracking: false,
  enable_health_monitoring: false, require_member_for_session: false,
  require_print_before_release: false, enable_assigned_time_limit: false,
};

describe('NavShell flag gating', () => {
  beforeEach(() => useFeatureFlagStore.getState().clear());

  it('hides Members and Events nav when both flags off', () => {
    useFeatureFlagStore.getState().setFlags({ ...BASE });
    render(<MemoryRouter><NavShell><div>child</div></NavShell></MemoryRouter>);
    expect(screen.queryByText('Members')).not.toBeInTheDocument();
    expect(screen.queryByText('Events')).not.toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('shows Members when enable_members on, Events hidden', () => {
    useFeatureFlagStore.getState().setFlags({ ...BASE, enable_members: true });
    render(<MemoryRouter><NavShell><div>child</div></NavShell></MemoryRouter>);
    expect(screen.getByText('Members')).toBeInTheDocument();
    expect(screen.queryByText('Events')).not.toBeInTheDocument();
  });

  it('shows Events when enable_tournaments on', () => {
    useFeatureFlagStore.getState().setFlags({ ...BASE, enable_tournaments: true });
    render(<MemoryRouter><NavShell><div>child</div></NavShell></MemoryRouter>);
    expect(screen.getByText('Events')).toBeInTheDocument();
  });

  it('shows both when both flags on', () => {
    useFeatureFlagStore.getState().setFlags({ ...BASE, enable_members: true, enable_tournaments: true });
    render(<MemoryRouter><NavShell><div>child</div></NavShell></MemoryRouter>);
    expect(screen.getByText('Members')).toBeInTheDocument();
    expect(screen.getByText('Events')).toBeInTheDocument();
  });
});
