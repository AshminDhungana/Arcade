import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/authStore';

export async function patchSettings(updates: Record<string, string>, token: string | null): Promise<Record<string, string>> {
  const res = await fetch('/api/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(updates),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update settings' }));
    throw new Error(err.detail ?? `Update failed: ${res.status}`);
  }
  return (await res.json()) as Record<string, string>;
}

export function useToggleFlag() {
  const token = useAuthStore((s) => s.accessToken);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { key: string; value: boolean }) =>
      patchSettings({ [vars.key]: vars.value ? 'true' : 'false' }, token),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['featureFlags'] }); },
  });
}
