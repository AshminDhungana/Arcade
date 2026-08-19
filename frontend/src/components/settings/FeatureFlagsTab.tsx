import { FLAG_KEYS, CONFIG_KEYS } from '@/api/featureFlags';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { useToggleFlag } from '@/api/settings';
import { Switch } from '@/components/ui/Switch';
import { Input } from '@/components/ui/Input';
import { toast } from '@/store/toastStore';

const GROUPS = {
  'Core Features': [
    'enable_members',
    'enable_packages',
    'enable_pos',
    'enable_reservations',
    'enable_wake_on_lan',
  ],
  'Operations': [
    'enable_inventory',
    'enable_vouchers',
    'enable_tournaments',
    'enable_expense_tracking',
    'enable_health_monitoring',
    'enable_remote_commands',
    'enable_analytics',
    'enable_promotions',
    'enable_maintenance_mode',
  ],
  'Agent/Overlay': [
    'enable_tuya',
    'enable_kiosk_branding',
    'overlay_pauses_billing',
    'require_member_for_session',
    'enable_assigned_time_limit',
  ],
  'Advanced': [
    'require_print_before_release',
    'block_shift_close_unprinted',
    'enable_loyalty_discounts',
    'enable_audit_export',
  ],
};

const CONFIG_GROUPS = {
  'Advanced': ['shift_cash_variance_threshold'],
};

const FLAG_LABELS: Record<string, string> = {
  enable_members: 'Members & Wallet',
  enable_packages: 'Time Packages',
  enable_pos: 'POS (Food/Drink)',
  enable_reservations: 'Reservations',
  enable_wake_on_lan: 'Wake-on-LAN',
  enable_inventory: 'Inventory',
  enable_vouchers: 'Vouchers',
  enable_tournaments: 'Tournaments',
  enable_expense_tracking: 'Expense Tracking',
  enable_health_monitoring: 'Health Monitoring',
  enable_remote_commands: 'Remote Commands (H.1-H.4)',
  enable_analytics: 'Analytics Dashboard (K.1-K.3)',
  enable_promotions: 'Promotions Engine',
  enable_maintenance_mode: 'Maintenance Mode (C.11)',
  enable_tuya: 'Tuya Smart Plugs',
  enable_kiosk_branding: 'Kiosk Branding',
  overlay_pauses_billing: 'Overlay Pauses Billing',
  require_member_for_session: 'Require Member for Session',
  enable_assigned_time_limit: 'Assigned Time Limit',
  require_print_before_release: 'Require Print Before Release',
  block_shift_close_unprinted: 'Block Shift Close Unprinted',
  enable_loyalty_discounts: 'Loyalty Discounts (F.4)',
  enable_audit_export: 'Audit Export',
};

const FLAG_DESCRIPTIONS: Record<string, string> = {
  enable_members: 'Show the Members management surface',
  enable_packages: 'Enable Packages and pricing management',
  enable_pos: 'Enable POS sales and billing',
  enable_reservations: 'Enable seat reservations',
  enable_wake_on_lan: 'Send Wake-on-LAN magic packets on boot',
  enable_inventory: 'Enable inventory tracking',
  enable_vouchers: 'Enable voucher codes and promotions',
  enable_tournaments: 'Enable tournament management',
  enable_expense_tracking: 'Enable expense tracking and reports',
  enable_health_monitoring: 'Enable agent health monitoring',
  enable_remote_commands: 'Enable remote restart/shutdown/message/screenshot (Section H)',
  enable_analytics: 'Enable analytics dashboard & reports (Section K)',
  enable_promotions: 'Enable promotions engine (happy hour, flash, etc.)',
  enable_maintenance_mode: 'Enable seat maintenance mode (C.11)',
  enable_tuya: 'Enable Tuya smart plug control',
  enable_kiosk_branding: 'Enable custom cafe branding on agent overlay',
  overlay_pauses_billing: 'Pause excludes time from billing calculation',
  require_member_for_session: 'Require a member to start a session',
  enable_assigned_time_limit: 'Allow capping a session with a time limit that auto-locks the seat at expiry',
  require_print_before_release: 'Block seat release until invoice printed',
  block_shift_close_unprinted: 'Block shift close if unprinted invoices exist',
  enable_loyalty_discounts: 'Enable tier-based loyalty discounts at checkout (F.4)',
  enable_audit_export: 'Enable audit log export/download',
};

const CONFIG_LABELS: Record<string, string> = {
  shift_cash_variance_threshold: 'Shift Cash Variance Threshold (paise)',
};

const CONFIG_DESCRIPTIONS: Record<string, string> = {
  shift_cash_variance_threshold: 'Paise threshold for shift variance flag',
};

export function FeatureFlagsTab() {
  const flags = useFeatureFlagStore((s) => s.flags);
  const toggle = useToggleFlag();

  const anyPending = toggle.isPending;

  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        Feature Flags
      </h2>

      {anyPending && (
        <div className="mb-4 text-xs text-amber-400 flex items-center gap-1">
          <span className="animate-pulse">●</span>
          <span>Saving…</span>
        </div>
      )}

      <div className="space-y-6" role="list" aria-label="Feature flags">
        {Object.entries(GROUPS).map(([groupName, keys]) => (
          <section key={groupName} className="space-y-3">
            <h3 className="text-lg font-medium text-gray-900">{groupName}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {keys.map((key) => (
                <div key={key} className="flex flex-col gap-2">
                  <Switch
                    checked={flags[key] as boolean}
                    disabled={toggle.isPending}
                    onCheckedChange={(value) =>
                      toggle.mutate(
                        { key, value },
                        {
                          onSuccess: () => {
                            const label = FLAG_LABELS[key];
                            toast.success(`${label} ${value ? 'enabled' : 'disabled'}`);
                          },
                          onError: (err: Error) => {
                            const label = FLAG_LABELS[key];
                            toast.error(`Failed to toggle ${label}: ${err.message}`);
                          },
                        }
                      )
                    }
                    label={FLAG_LABELS[key]}
                    description={FLAG_DESCRIPTIONS[key]}
                  />
                </div>
              ))}
            </div>
          </section>
        ))}

        {Object.entries(CONFIG_GROUPS).map(([groupName, keys]) => (
          <section key={groupName} className="space-y-3">
            <h3 className="text-lg font-medium text-gray-900">{groupName}</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {keys.map((key) => (
                <div key={key} className="flex flex-col gap-2">
                  <label className="text-sm text-gray-700">{CONFIG_LABELS[key]}</label>
                  <Input
                    type="number"
                    value={flags[key] as number}
                    onChange={(e) =>
                      toggle.mutate(
                        { key, value: parseInt(e.target.value, 10) },
                        {
                          onSuccess: () => {
                            const label = CONFIG_LABELS[key];
                            toast.success(`${label} updated`);
                          },
                          onError: (err: Error) => {
                            const label = CONFIG_LABELS[key];
                            toast.error(`Failed to update ${label}: ${err.message}`);
                          },
                        }
                      )
                    }
                    description={CONFIG_DESCRIPTIONS[key]}
                  />
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
