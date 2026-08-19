import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import type { AppSettings } from '@/types/pos';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { useAuthStore } from '@/store/authStore';

const API_BASE = '/api';

/** All recognised feature flag keys (20 boolean flags). */
export const FLAG_KEYS = [
  // Core Features
  'enable_members',
  'enable_packages',
  'enable_pos',
  'enable_reservations',
  'enable_wake_on_lan',
  // Operations
  'enable_inventory',
  'enable_vouchers',
  'enable_tournaments',
  'enable_expense_tracking',
  'enable_health_monitoring',
  'enable_remote_commands',
  'enable_analytics',
  'enable_promotions',
  'enable_maintenance_mode',
  // Agent/Overlay
  'enable_tuya',
  'enable_kiosk_branding',
  'overlay_pauses_billing',
  'require_member_for_session',
  'enable_assigned_time_limit',
  // Advanced
  'require_print_before_release',
  'block_shift_close_unprinted',
  'enable_loyalty_discounts',
  'enable_audit_export',
] as const;

/** Config keys (numbers/strings). */
export const CONFIG_KEYS = [
  'shift_cash_variance_threshold',
  // Add other config keys here as needed
] as const;

export type FlagKey = typeof FLAG_KEYS[number];
export type ConfigKey = typeof CONFIG_KEYS[number];

/** Fetch all settings from the backend and extract feature flags. */
export async function fetchFeatureFlags(token: string | null): Promise<AppSettings> {
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/settings`, { headers });
  if (!res.ok) {
    throw new Error(`Failed to fetch settings: ${res.status} ${res.statusText}`);
  }

  const data = (await res.json()) as Record<string, string>;

  // Parse all recognised keys
  const settings: Partial<AppSettings> = {};
  for (const key of FLAG_KEYS) {
    const value = data[key];
    settings[key as FlagKey] = value?.toLowerCase() === 'true';
  }
  for (const key of CONFIG_KEYS) {
    const value = data[key];
    settings[key as ConfigKey] = value ? parseFloat(value) : 0;
  }
  return settings as AppSettings;
}

/** React Query hook that fetches feature flags and syncs them to the Zustand store.
 *  Call once at the App level to bootstrap flags on mount. */
export function useFeatureFlags() {
  const token = useAuthStore((s) => s.accessToken);
  const setFlags = useFeatureFlagStore((s) => s.setFlags);

  const query = useQuery({
    queryKey: ['featureFlags'],
    queryFn: () => fetchFeatureFlags(token),
    // Only fetch once authenticated — /api/settings requires cashier+ auth,
    // so calling this at app root (e.g. on the /login route) before a
    // token exists would 401. Gating also makes the query re-run with the
    // token once login populates the store (enabled: false -> true).
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: 3,
  });

  // Sync to Zustand store whenever data arrives
  useEffect(() => {
    if (query.data) {
      setFlags(query.data);
    }
  }, [query.data, setFlags]);

  return query;
}
