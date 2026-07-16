import { create } from 'zustand';
import type { FeatureFlags } from '@/types/pos';

/** Default feature flags — all OFF until loaded from backend. */
const DEFAULT_FLAGS: FeatureFlags = {
  enable_members: false,
  enable_packages: false,
  enable_pos: false,
  enable_inventory: false,
  enable_reservations: false,
  enable_vouchers: false,
  enable_tournaments: false,
  enable_expense_tracking: false,
  enable_health_monitoring: false,
  require_member_for_session: false,
  require_print_before_release: false,
};

interface FeatureFlagStore {
  flags: FeatureFlags;
  /** True once flags have been fetched from the backend at least once. */
  flagsLoaded: boolean;

  /** Replace all flags with new values (called after fetch). */
  setFlags: (flags: FeatureFlags) => void;

  /** Read a single flag by key name. */
  getFlag: (name: keyof FeatureFlags) => boolean;

  /** Reset all flags to defaults. */
  clear: () => void;
}

export const useFeatureFlagStore = create<FeatureFlagStore>((set, get) => ({
  flags: { ...DEFAULT_FLAGS },
  flagsLoaded: false,

  setFlags: (flags) => set({ flags, flagsLoaded: true }),

  getFlag: (name) => get().flags[name] ?? false,

  clear: () => set({ flags: { ...DEFAULT_FLAGS }, flagsLoaded: false }),
}));
