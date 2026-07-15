export const CHART = {
  grid: '#334155', // slate-700
  axis: '#94A3B8', // slate-400
  revenue: '#3B82F6', // blue-500
  pos: '#A78BFA', // violet-400
  trend: '#22C55E', // green-500
} as const;

export const tooltipStyle = {
  backgroundColor: '#0F172A', // surface-900
  border: '1px solid #334155',
  borderRadius: 8,
  color: '#F8FAFC',
  fontSize: 12,
} as const;

export const AXIS_PROPS = {
  stroke: CHART.axis,
  tick: { fill: CHART.axis, fontSize: 12 },
  tickLine: false,
} as const;
