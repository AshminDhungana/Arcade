import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { formatPaise } from '@/hooks/useFormatPaise';
import { formatWeekday } from './format';
import { CHART, tooltipStyle, AXIS_PROPS } from './chartTheme';
import type { DailyRevenue } from '@/types/analytics';

export function RevenueBarChart({ data }: { data: DailyRevenue[] }) {
  const chartData = data.map((d) => ({ ...d, label: formatWeekday(d.date) }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="label" {...AXIS_PROPS} />
        <YAxis
          {...AXIS_PROPS}
          width={48}
          tickFormatter={(v: number) => `₹${(v / 100).toFixed(0)}`}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          cursor={{ fill: 'rgba(148,163,184,0.12)' }}
          formatter={(value) => [formatPaise(Number(value)), 'Revenue']}
        />
        <Bar dataKey="total_paise" fill={CHART.revenue} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
