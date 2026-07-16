import { describe, it, expect, beforeEach } from 'vitest';
import { useFeatureFlagStore } from './featureFlagStore';

const SAMPLE = {
  enable_members: true,
  enable_packages: false,
  enable_pos: false,
  enable_inventory: false,
  enable_reservations: false,
  enable_vouchers: false,
  enable_tournaments: false,
  enable_expense_tracking: false,
  enable_health_monitoring: false,
  require_member_for_session: false,
};

describe('featureFlagStore', () => {
  beforeEach(() => {
    useFeatureFlagStore.getState().clear();
  });

  it('starts with flagsLoaded false', () => {
    expect(useFeatureFlagStore.getState().flagsLoaded).toBe(false);
  });

  it('setFlags sets flagsLoaded true', () => {
    useFeatureFlagStore.getState().setFlags({ ...SAMPLE });
    expect(useFeatureFlagStore.getState().flagsLoaded).toBe(true);
  });

  it('clear resets flagsLoaded false', () => {
    useFeatureFlagStore.getState().setFlags({ ...SAMPLE });
    useFeatureFlagStore.getState().clear();
    expect(useFeatureFlagStore.getState().flagsLoaded).toBe(false);
  });
});
