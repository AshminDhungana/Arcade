import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import type { FeatureFlags } from '@/types/pos';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { useAuthStore } from '@/store/authStore';

const API_BASE = '/api';

/** All recognised feature flag keys. */
export const FLAG_KEYS: (keyof FeatureFlags)[] = [
  'enable_members',
  'enable_packages',
  'enable_pos',
  'enable_inventory',
  'enable_reservations',
  'enable_vouchers',
  'enable_tournaments',
  'enable_expense_tracking',
  'enable_health_monitoring',
  'require_member_for_session',
];

/** Fetch all settings from the backend and extract feature flags. */
export async function fetchFeatureFlags(token: string | null): Promise<FeatureFlags> {
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/settings`, { headers });
  if (!res.ok) {
    throw new Error(`Failed to fetch settings: ${res.status} ${res.statusText}`);
  }

  const data = (await res.json()) as Record<string, string>;

  // Parse only recognised flag keys, defaulting to false
  const flags: Record<string, boolean> = {};
  for (const key of FLAG_KEYS) {
    const value = data[key];
    flags[key] = value?.toLowerCase() === 'true';
  }
  return flags as unknown as FeatureFlags;
}

/** React Query hook that fetches feature flags and syncs them to the Zustand store.
 *  Call once at the App level to bootstrap flags on mount. */
export function useFeatureFlags() {
  const token = useAuthStore((s) => s.accessToken);
  const setFlags = useFeatureFlagStore((s) => s.setFlags);

  const query = useQuery({
    queryKey: ['featureFlags'],
    queryFn: () => fetchFeatureFlags(token),
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
