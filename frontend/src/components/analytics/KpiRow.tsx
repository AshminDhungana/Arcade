import { IndianRupee, Activity, Timer, Clock } from 'lucide-react';
import { formatPaise } from '@/hooks/useFormatPaise';
import { formatDuration, formatHour } from './format';
import type { AnalyticsSummary } from '@/types/analytics';
import { KpiCard } from './KpiCard';

export function KpiRow({ summary }: { summary: AnalyticsSummary }) {
  const busiest = summary.busiest_hour ? formatHour(summary.busiest_hour.hour) : '—';
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard label="Today's revenue" value={formatPaise(summary.total_revenue_paise)} icon={IndianRupee} sublabel="Today" />
      <KpiCard label="Sessions" value={String(summary.session_count)} icon={Activity} sublabel="Started today" />
      <KpiCard label="Avg duration" value={formatDuration(summary.average_duration_seconds)} icon={Timer} sublabel="Completed sessions" />
      <KpiCard label="Busiest hour" value={busiest} icon={Clock} sublabel="By session count" />
    </div>
  );
}
