import { useEffect, useState } from 'react';
import { patchSettings, useSettings } from '@/api/settings';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState } from '@/components/ui/ErrorState';
import { toast } from '@/store/toastStore';
import { useAuthStore } from '@/store/authStore';

export function BroadcastTab() {
  const { data: settings, isLoading, isError, refetch } = useSettings();
  const token = useAuthStore((s) => s.accessToken);
  const [banner, setBanner] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) setBanner(settings['event_banner'] ?? '');
  }, [settings]);

  const handleChange = (value: string) => {
    setBanner(value);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await patchSettings({ event_banner: banner }, token);
      toast.success('Event banner saved');
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to save event banner';
      toast.error(msg.includes('401') || msg.includes('403') ? 'Admin required' : msg);
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-foreground">Broadcast</h1>
        <div className="flex h-64 items-center justify-center text-muted-foreground">Loading…</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-foreground">Broadcast</h1>

      {isError && (
        <ErrorState message="Failed to load broadcast settings. Admin required." onRetry={refetch} />
      )}

      <section className="rounded-xl border border-border bg-card p-5">
        <form onSubmit={handleSave} className="max-w-md space-y-4">
          <Input
            name="event_banner"
            label="Event banner"
            value={banner}
            onChange={(e) => handleChange(e.target.value)}
            placeholder="e.g. Weekend Tournament (shown on the kiosk when set)"
          />

          <div className="flex justify-end">
            <Button type="submit" variant="emerald" loading={saving}>
              Save
            </Button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default BroadcastTab;
