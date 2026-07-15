import { useAnalyticsSummary } from '@/api/analytics';
import { useSeats } from '@/api/seats';
import { ErrorState } from '@/components/ui/ErrorState';
import { formatPaise } from '@/hooks/useFormatPaise';
import { KpiRow } from '@/components/analytics/KpiRow';
import { ChartCard } from '@/components/analytics/ChartCard';
import { RevenueBarChart } from '@/components/analytics/RevenueBarChart';
import { SeatUtilisationChart } from '@/components/analytics/SeatUtilisationChart';
import { TopPosItemsChart } from '@/components/analytics/TopPosItemsChart';
import { MemberTrendChart } from '@/components/analytics/MemberTrendChart';
import { HealthAlerts } from '@/components/analytics/HealthAlerts';

function sumPaise(items: { total_paise: number }[]): number {
  return items.reduce((s, d) => s + d.total_paise, 0);
}

export function AnalyticsPage() {
  const { data: summary, isLoading, isError, error, refetch } = useAnalyticsSummary();
  const { data: seats = [] } = useSeats();

  if (isLoading) {
    return (
      <div
        className="flex h-64 items-center justify-center text-slate-400"
        role="status"
        aria-label="Loading analytics"
      >
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-700 border-t-blue-500" />
        <span className="ml-3">Loading analytics…</span>
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState
        message={error?.message ?? 'Failed to load analytics.'}
        onRetry={() => refetch()}
      />
    );
  }

  if (!summary) return null;

  const weeklyTotal = sumPaise(summary.weekly_revenue);

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <h1 className="text-2xl font-semibold text-white">Analytics</h1>

      <KpiRow summary={summary} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCard
          title="Weekly revenue"
          description="Last 7 days"
          ariaLabel={`Weekly revenue bar chart, last 7 days, total ${formatPaise(weeklyTotal)}`}
          isEmpty={summary.weekly_revenue.length === 0}
        >
          <RevenueBarChart data={summary.weekly_revenue} />
        </ChartCard>

        <ChartCard
          title="Seat utilisation"
          description="By zone, last 7 days"
          ariaLabel="Seat utilisation bar chart by zone for the last 7 days"
          isEmpty={summary.zone_utilisation.length === 0}
        >
          <SeatUtilisationChart data={summary.zone_utilisation} />
        </ChartCard>

        <ChartCard
          title="Top POS items"
          description="Top sellers by quantity, last 30 days"
          ariaLabel="Top point-of-sale items horizontal bar chart by quantity sold"
          isEmpty={summary.top_pos_items.length === 0}
        >
          <TopPosItemsChart data={summary.top_pos_items} />
        </ChartCard>

        <ChartCard
          title="Member registrations"
          description="New members, last 30 days"
          ariaLabel="Member registration trend line chart for the last 30 days"
          isEmpty={summary.member_registration_trend.length === 0}
        >
          <MemberTrendChart data={summary.member_registration_trend} />
        </ChartCard>
      </div>

      <HealthAlerts alerts={summary.health_alerts} seats={seats} />
    </main>
  );
}

export default AnalyticsPage;
