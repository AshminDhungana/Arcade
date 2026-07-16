import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import RequireFeature from './RequireFeature';
import { useFeatureFlagStore } from '@/store/featureFlagStore';

const ALL_OFF = {
  enable_members: false, enable_packages: false, enable_pos: false,
  enable_inventory: false, enable_reservations: false, enable_vouchers: false,
  enable_tournaments: false, enable_expense_tracking: false,
  enable_health_monitoring: false, require_member_for_session: false,
};
const ALL_ON = { ...ALL_OFF, enable_members: true, enable_tournaments: true };

describe('RequireFeature', () => {
  beforeEach(() => useFeatureFlagStore.getState().clear());

  it('renders children once flags are loaded and flag is on', () => {
    useFeatureFlagStore.getState().setFlags(ALL_ON);
    render(<RequireFeature flag="enable_members"><div>Members</div></RequireFeature>);
    expect(screen.getByText('Members')).toBeInTheDocument();
  });

  it('renders FeatureUnavailable when flag is off after load', () => {
    useFeatureFlagStore.getState().setFlags({ ...ALL_ON, enable_members: false });
    render(
      <MemoryRouter>
        <RequireFeature flag="enable_members"><div>Members</div></RequireFeature>
      </MemoryRouter>,
    );
    expect(screen.getByText(/is unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText('Members')).not.toBeInTheDocument();
  });

  it('renders children while flags are still loading (fail-open)', () => {
    // flagsLoaded stays false after clear()
    render(<RequireFeature flag="enable_members"><div>Members</div></RequireFeature>);
    expect(screen.getByText('Members')).toBeInTheDocument();
  });
});
