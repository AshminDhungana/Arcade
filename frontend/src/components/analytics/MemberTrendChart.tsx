import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { formatWeekday } from './format';
import { CHART, tooltipStyle, AXIS_PROPS } from './chartTheme';
import type { DailyCount } from '@/types/analytics';

export function MemberTrendChart({ data }: { data: DailyCount[] }) {
  const chartData = data.map((d) => ({ ...d, label: formatWeekday(d.date) }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="label" {...AXIS_PROPS} />
        <YAxis {...AXIS_PROPS} width={32} allowDecimals={false} />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(value) => [`${Number(value)}`, 'New members']}
        />
        <Line
          type="monotone"
          dataKey="count"
          stroke={CHART.trend}
          strokeWidth={2}
          dot={{ r: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
