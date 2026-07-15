import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { CHART, tooltipStyle, AXIS_PROPS } from './chartTheme';
import type { TopPosItem } from '@/types/analytics';

export function TopPosItemsChart({ data }: { data: TopPosItem[] }) {
  const chartData = [...data].reverse(); // largest on top for horizontal layout
  return (
    <ResponsiveContainer width="100%" height={Math.max(200, chartData.length * 36)}>
      <BarChart
        layout="vertical"
        data={chartData}
        margin={{ top: 8, right: 16, left: 8, bottom: 0 }}
      >
        <CartesianGrid stroke={CHART.grid} horizontal={false} />
        <XAxis type="number" {...AXIS_PROPS} />
        <YAxis type="category" dataKey="name" {...AXIS_PROPS} width={96} />
        <Tooltip
          contentStyle={tooltipStyle}
          cursor={{ fill: 'rgba(148,163,184,0.1)' }}
          formatter={(value) => [`${Number(value)}`, 'Sold']}
        />
        <Bar dataKey="quantity" fill={CHART.pos} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
