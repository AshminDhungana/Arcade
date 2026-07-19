import { useEffect, useState } from 'react';
import {
  patchSettings,
  useSettings,
  parsePrinterConfig,
  type PrinterConfig,
} from '@/api/settings';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState } from '@/components/ui/ErrorState';
import { toast } from '@/store/toastStore';
import { useAuthStore } from '@/store/authStore';

const EMPTY: PrinterConfig = { type: '', vendor: '', product: '' };

export function PrinterTab() {
  const { data: settings, isLoading, isError, refetch } = useSettings();
  const token = useAuthStore((s) => s.accessToken);
  const [form, setForm] = useState<PrinterConfig>(EMPTY);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) setForm(parsePrinterConfig(settings));
  }, [settings]);

  const handleChange = (field: keyof PrinterConfig, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await patchSettings(
        {
          printer_type: form.type,
          printer_usb_vendor: form.vendor,
          printer_usb_product: form.product,
        },
        token,
      );
      toast.success('Printer settings saved');
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to save printer settings';
      toast.error(msg.includes('403') || msg.includes('401') ? 'Admin required' : msg);
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-semibold text-foreground">Printer</h1>
        <div className="flex h-64 items-center justify-center text-muted-foreground">Loading…</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-foreground">Printer</h1>

      {isError && (
        <ErrorState message="Failed to load printer settings. Admin required." onRetry={refetch} />
      )}

      <section className="rounded-xl border border-border bg-card p-5">
        <form onSubmit={handleSave} className="max-w-md space-y-4">
          <div>
            <label
              htmlFor="printer_type"
              className="mb-1 block text-sm font-medium text-foreground"
            >
              Connection type
            </label>
            <select
              id="printer_type"
              value={form.type}
              onChange={(e) => handleChange('type', e.target.value)}
              className="w-full rounded-lg border border-input bg-popover py-2.5 px-3 text-sm text-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="">Select…</option>
              <option value="usb">USB</option>
              <option value="network">Network</option>
            </select>
          </div>

          <Input
            name="printer_usb_vendor"
            label="USB vendor ID"
            value={form.vendor}
            onChange={(e) => handleChange('vendor', e.target.value)}
            placeholder="e.g. 0x0416"
          />
          <Input
            name="printer_usb_product"
            label="USB product ID"
            value={form.product}
            onChange={(e) => handleChange('product', e.target.value)}
            placeholder="e.g. 0x5011"
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

export default PrinterTab;
