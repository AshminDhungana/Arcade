import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { utilisationColor } from './format';
import { CHART, tooltipStyle, AXIS_PROPS } from './chartTheme';
import type { ZoneUtilisation } from '@/types/analytics';

export function SeatUtilisationChart({ data }: { data: ZoneUtilisation[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="zone_name" {...AXIS_PROPS} />
        <YAxis {...AXIS_PROPS} width={40} domain={[0, 100]} unit="%" />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(value) => [`${Number(value)}%`, 'Utilisation']}
        />
        <Bar dataKey="utilisation_pct" radius={[4, 4, 0, 0]}>
          {data.map((z) => (
            <Cell key={z.zone_id} fill={utilisationColor(z.utilisation_pct)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
