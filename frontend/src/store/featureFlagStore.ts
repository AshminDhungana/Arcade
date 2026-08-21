import { create } from 'zustand';
import type { AppSettings } from '@/types/pos';
import type { FlagKey, ConfigKey } from '@/api/featureFlags';

/** Default feature flags — all OFF until loaded from backend. */
const DEFAULT_FLAGS: AppSettings = {
  // Core Features
  enable_members: true,
  enable_packages: true,
  enable_pos: true,
  enable_reservations: true,
  enable_wake_on_lan: true,
  // Operations
  enable_inventory: false,
  enable_vouchers: false,
  enable_tournaments: false,
  enable_expense_tracking: false,
  enable_health_monitoring: true,
  enable_remote_commands: false,
  enable_analytics: false,
  enable_promotions: false,
  enable_maintenance_mode: false,
  // Agent/Overlay
  enable_tuya: false,
  enable_kiosk_branding: false,
  overlay_pauses_billing: true,
  require_member_for_session: false,
  enable_assigned_time_limit: false,
  // Advanced
  require_print_before_release: false,
  block_shift_close_unprinted: false,
  enable_loyalty_discounts: false,
  enable_audit_export: false,
  // Agent
  agent_auto_start: false,
  // Config
  shift_cash_variance_threshold: 5000,
};

interface FeatureFlagStore {
  flags: AppSettings;
  /** True once flags have been fetched from the backend at least once. */
  flagsLoaded: boolean;

  /** Replace all flags with new values (called after fetch). */
  setFlags: (flags: Partial<AppSettings>) => void;

  /** Read a single flag by key name. */
  getFlag: (name: FlagKey | ConfigKey) => boolean | number;

  /** Reset all flags to defaults. */
  clear: () => void;
}

export const useFeatureFlagStore = create<FeatureFlagStore>((set, get) => ({
  flags: { ...DEFAULT_FLAGS },
  flagsLoaded: false,

  setFlags: (flags) => set((state) => ({ flags: { ...state.flags, ...flags } as AppSettings, flagsLoaded: true })),

  getFlag: (name) => get().flags[name] ?? false,

  clear: () => set({ flags: { ...DEFAULT_FLAGS }, flagsLoaded: false }),
}));
