import { Link } from 'react-router-dom';

const LABELS: Record<string, string> = {
  enable_members: 'Members',
  enable_packages: 'Packages',
  enable_pos: 'Point of Sale',
  enable_inventory: 'Inventory',
  enable_reservations: 'Reservations',
  enable_vouchers: 'Vouchers & Promotions',
  enable_tournaments: 'Tournaments',
  enable_expense_tracking: 'Expense Tracking',
  enable_health_monitoring: 'Health Monitoring',
  require_member_for_session: 'Member-only Sessions',
};

export default function FeatureUnavailable({ flag }: { flag: string }) {
  const label = LABELS[flag] ?? 'This feature';
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-900 p-6 text-center">
      <div className="rounded-2xl bg-slate-800 p-5 text-slate-500">
        <svg className="h-10 w-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
        </svg>
      </div>
      <h1 className="text-xl font-semibold text-white">{label} is unavailable</h1>
      <p className="max-w-sm text-sm text-slate-400">
        This feature is turned off. Enable it from Settings → Feature Flags to use it.
      </p>
      <Link
        to="/"
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        Return to Dashboard
      </Link>
    </main>
  );
}
