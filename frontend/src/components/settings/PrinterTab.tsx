import { useEffect, useState } from 'react';
import {
  patchSettings,
  useSettings,
  parsePrinterConfig,
  type PrinterConfig,
  useDiscoveredPrinters,
  type DiscoveredPrinter,
} from '@/api/settings';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ErrorState } from '@/components/ui/ErrorState';
import { toast } from '@/store/toastStore';
import { useAuthStore } from '@/store/authStore';
import { ChevronDown, CheckCircle, Printer, Settings, Usb, Wifi } from 'lucide-react';

const EMPTY: PrinterConfig = { type: '', vendor: '', product: '' };

const CONNECTION_BADGES: Record<DiscoveredPrinter['connection_type'], {
  icon: React.ReactNode;
  label: string;
  className: string;
}> = {
  usb: { icon: <Usb className="w-3.5 h-3.5" />, label: 'USB', className: 'bg-amber-100 text-amber-800 border-amber-300' },
  network: { icon: <Wifi className="w-3.5 h-3.5" />, label: 'Network', className: 'bg-blue-100 text-blue-800 border-blue-300' },
};

export function PrinterTab() {
  const { data: settings, isLoading, isError, refetch } = useSettings();
  const { data: discoveredPrinters, isLoading: discovering, refetch: refetchDiscovered } = useDiscoveredPrinters();
  const token = useAuthStore((s) => s.accessToken);
  const [form, setForm] = useState<PrinterConfig>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [discoverOpen, setDiscoverOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);

  useEffect(() => {
    if (settings) setForm(parsePrinterConfig(settings));
  }, [settings]);

  const handleChange = (field: keyof PrinterConfig, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleDiscover = async () => {
    setDiscoverOpen(true);
    try {
      await refetchDiscovered();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to discover printers';
      toast.error(msg.includes('403') || msg.includes('401') ? 'Admin required' : msg);
    }
  };

  const handleSelectPrinter = (printer: DiscoveredPrinter) => {
    // Auto-populate the form based on discovered printer
    if (printer.connection_type === 'usb') {
      setForm({
        type: 'usb',
        vendor: '', // USB vendor/product not reliably extractable from URI cross-platform
        product: '',
      });
    } else {
      setForm({
        type: 'network',
        vendor: '',
        product: '',
      });
    }
    // Store the URI for saving
    setForm((prev) => ({ ...prev, uri: printer.uri }));
    // Also update the settings via PATCH
    patchSettings(
      {
        printer_type: printer.connection_type,
        printer_uri: printer.uri,
      },
      token,
    ).then(() => {
      toast.success(`Selected: ${printer.name}`);
      refetch();
      setDiscoverOpen(false);
    }).catch((err) => {
      const msg = err instanceof Error ? err.message : 'Failed to save printer selection';
      toast.error(msg.includes('403') || msg.includes('401') ? 'Admin required' : msg);
    });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const patch: Record<string, string> = {
        printer_type: form.type,
        printer_usb_vendor: form.vendor,
        printer_usb_product: form.product,
      };
      // Include URI if it was set via auto-detection
      const formWithUri = form as PrinterConfig & { uri?: string };
      if (formWithUri.uri) {
        patch['printer_uri'] = formWithUri.uri;
      }
      await patchSettings(patch, token);
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
      <h1 className="text-2xl font-semibold text-foreground flex items-center gap-2">
        <Printer className="w-5 h-5" /> Printer
      </h1>

      {isError && (
        <ErrorState message="Failed to load printer settings. Admin required." onRetry={refetch} />
      )}

      <section className="rounded-xl border border-border bg-card p-5 space-y-5">
        <form onSubmit={handleSave} className="max-w-2xl space-y-5">
          {/* Configured Printer Display */}
          {form.type && (
            <div className="rounded-lg border border-border bg-muted/50 p-4 space-y-3">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <Printer className="w-4 h-4" />
                <span>Currently Configured</span>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className={`px-2.5 py-1 rounded-full border text-xs font-medium ${
                  form.type === 'usb'
                    ? 'bg-amber-100 text-amber-800 border-amber-300'
                    : 'bg-blue-100 text-blue-800 border-blue-300'
                }`}>
                  {form.type === 'usb' ? 'USB' : 'Network'}
                </span>
                {(form.vendor || form.product) && (
                  <span className="text-muted-foreground font-mono text-xs">
                    {form.vendor && `VID: ${form.vendor}`} {form.product && `PID: ${form.product}`}
                  </span>
                )}
                {(form as PrinterConfig & { uri?: string }).uri && (
                  <span className="text-muted-foreground font-mono text-xs truncate max-w-xs">
                    URI: {(form as PrinterConfig & { uri?: string }).uri}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Connection Type Selector */}
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
              className="w-full max-w-md rounded-lg border border-input bg-popover py-2.5 px-3 text-sm text-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="">Select…</option>
              <option value="usb">USB</option>
              <option value="network">Network</option>
            </select>
          </div>

          {/* USB Vendor/Product Inputs (shown when USB selected) */}
          {form.type === 'usb' && (
            <div className="grid gap-4 sm:grid-cols-2">
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
            </div>
          )}

          {/* Network URI Input (shown when network selected) */}
          {form.type === 'network' && (
            <Input
              name="printer_uri"
              label="Network printer URI"
              value={(form as PrinterConfig & { uri?: string }).uri || ''}
              onChange={(e) => handleChange('uri' as keyof PrinterConfig, e.target.value)}
              placeholder="e.g. socket://192.168.1.100:9100 or ipp://printer.local:631/ipp/print"
            />
          )}

          {/* Discover Printers Button */}
          <div className="pt-2 border-t border-border">
            <Button
              type="button"
              variant="outline"
              onClick={handleDiscover}
              disabled={discovering}
              className="w-full max-w-md justify-start gap-2"
            >
              <Settings className="w-4 h-4" />
              <span>{discovering ? 'Discovering…' : 'Detect Printers'}</span>
            </Button>
            <p className="mt-2 text-xs text-muted-foreground">
              Scans the server for USB and network printers. Admin required.
            </p>
          </div>

          {/* Discovered Printers List (Collapsible) */}
          {discoverOpen && discoveredPrinters && discoveredPrinters.length > 0 && (
            <div className="rounded-lg border border-border bg-card p-4 space-y-3 animate-in slide-in-from-top-2">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-foreground">Detected Printers ({discoveredPrinters.length})</h3>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setDiscoverOpen(false)}
                >
                  × Close
                </Button>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {discoveredPrinters.map((printer) => {
                  const badge = CONNECTION_BADGES[printer.connection_type];
                  return (
                    <Button
                      key={printer.name}
                      type="button"
                      variant="outline"
                      className="w-full justify-start text-left gap-3 p-3 h-auto"
                      onClick={() => handleSelectPrinter(printer)}
                    >
                      <div className="flex items-center gap-2">
                        <Printer className="w-5 h-5 text-muted-foreground" />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">{printer.name}</div>
                          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            {badge.icon}
                            <span className={`px-1.5 py-0.5 rounded border text-[10px] font-medium ${badge.className}`}>
                              {badge.label}
                            </span>
                            {printer.is_default && (
                              <span className="flex items-center gap-1 text-green-700">
                                <CheckCircle className="w-3 h-3" />
                                <span className="text-[10px] font-medium">Default</span>
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      {printer.description && (
                        <div className="ml-7 text-xs text-muted-foreground truncate">
                          {printer.description}
                        </div>
                      )}
                      {printer.make_and_model && (
                        <div className="ml-7 text-xs text-muted-foreground font-mono truncate">
                          {printer.make_and_model}
                        </div>
                      )}
                    </Button>
                  );
                })}
              </div>
              {discoveredPrinters.some(p => p.is_default) && (
                <p className="text-xs text-muted-foreground">
                  <CheckCircle className="w-3 h-3 inline-block" /> Default printer is marked
                </p>
              )}
            </div>
          )}

          {/* Empty state for discovery */}
          {discoverOpen && discoveredPrinters && discoveredPrinters.length === 0 && !discovering && (
            <div className="rounded-lg border border-dashed border-border bg-muted/30 p-6 text-center">
              <Printer className="w-10 h-10 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">No printers detected on the server.</p>
              <p className="text-xs text-muted-foreground mt-1">
                Ensure printers are installed on the server OS, then try again.
              </p>
            </div>
          )}

          {/* Advanced: Manual USB VID/PID Entry (Collapsible) */}
          <div className="border-t border-border pt-4">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="w-full justify-start gap-2 text-left"
              onClick={() => setAdvancedOpen(!advancedOpen)}
            >
              <ChevronDown className={`w-4 h-4 transition-transform ${advancedOpen ? 'rotate-180' : ''}`} />
              <span>Advanced: Manual USB Vendor/Product ID</span>
            </Button>
            {advancedOpen && (
              <div className="mt-3 grid gap-4 sm:grid-cols-2 animate-in slide-in-from-top-2">
                <Input
                  name="printer_usb_vendor"
                  label="USB vendor ID (hex)"
                  value={form.vendor}
                  onChange={(e) => handleChange('vendor', e.target.value)}
                  placeholder="e.g. 0x04b8"
                />
                <Input
                  name="printer_usb_product"
                  label="USB product ID (hex)"
                  value={form.product}
                  onChange={(e) => handleChange('product', e.target.value)}
                  placeholder="e.g. 0x0202"
                />
                <p className="sm:col-span-2 text-xs text-muted-foreground">
                  Use this when auto-detection doesn't find your USB printer.
                  Find IDs via <code className="font-mono">lsusb</code> (Linux/macOS) or Device Manager (Windows).
                </p>
              </div>
            )}
          </div>

          <div className="flex justify-end pt-2">
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
