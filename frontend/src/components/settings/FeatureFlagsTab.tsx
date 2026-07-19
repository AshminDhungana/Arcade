import { FLAG_KEYS } from '@/api/featureFlags';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import { useToggleFlag } from '@/api/settings';
import { Switch } from '@/components/ui/Switch';
import { toast } from '@/store/toastStore';

const FLAG_LABELS: Record<string, string> = {
  enable_members: 'Members',
  enable_packages: 'Packages',
  enable_pos: 'Point of Sale',
  enable_inventory: 'Inventory',
  enable_reservations: 'Reservations',
  enable_vouchers: 'Vouchers',
  enable_tournaments: 'Tournaments',
  enable_expense_tracking: 'Expense Tracking',
  enable_health_monitoring: 'Health Monitoring',
  require_member_for_session: 'Require Member for Session',
  require_print_before_release: 'Require Print Before Release',
  enable_assigned_time_limit: 'Assigned Time Limit',
};

const FLAG_DESCRIPTIONS: Record<string, string> = {
  enable_members: 'Show the Members management surface',
  enable_packages: 'Enable Packages and pricing management',
  enable_pos: 'Enable POS sales and billing',
  enable_inventory: 'Enable inventory tracking',
  enable_reservations: 'Enable seat reservations',
  enable_vouchers: 'Enable voucher codes and promotions',
  enable_tournaments: 'Enable tournament management',
  enable_expense_tracking: 'Enable expense tracking and reports',
  enable_health_monitoring: 'Enable agent health monitoring',
  require_member_for_session: 'Require a member to start a session',
  enable_assigned_time_limit:
    'Allow capping a session with a time limit that auto-locks the seat at expiry',
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

      <div className="space-y-4" role="list" aria-label="Feature flags">
        {FLAG_KEYS.map((key) => (
          <div key={key} className="flex items-center justify-between gap-4" role="listitem">
            <div className="flex-1 min-w-0">
              <Switch
                checked={flags[key]}
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
          </div>
        ))}
      </div>
    </section>
  );
}
