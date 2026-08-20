import { useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { Switch } from '@/components/ui/Switch';

interface AutoStartToggleProps {
  seatId: string;
}

async function setAutoStart(seatId: string, enabled: boolean): Promise<void> {
  const token = localStorage.getItem('access_token');
  const res = await fetch(`/api/seats/${seatId}/auto-start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error(`Failed to set auto-start: ${res.status}`);
}

export function AutoStartToggle({ seatId }: AutoStartToggleProps) {
  const { user } = useAuthStore();
  const { isEnabled } = useFeatureFlagStore();

  const isAdmin = user?.role === 'ADMIN';
  const autoStartEnabled = isEnabled('agent_auto_start');

  const [checked, setChecked] = useState(false);

  if (!isAdmin || !autoStartEnabled) {
    return null;
  }

  const handleToggle = async (enabled: boolean) => {
    setChecked(enabled);
    try {
      await setAutoStart(seatId, enabled);
    } catch (err) {
      console.error('Failed to set auto-start:', err);
      setChecked(!enabled); // Revert on error
    }
  };

  return (
    <label className="flex items-center gap-2">
      <Switch
        checked={checked}
        onCheckedChange={handleToggle}
        disabled={!isAdmin}
      />
      <span className="text-sm">Auto-Start on Boot</span>
    </label>
  );
}
