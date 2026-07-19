// Chart theme — colours are the design-system tokens (see src/index.css).
// Recharts renders SVG, so tokens are expressed as their hex values here.
export const CHART = {
  grid: '#334155', // --border
  axis: '#94a3b8', // --muted-foreground
  revenue: '#0090fa', // --primary
  pos: '#a78bfa', // violet-400 — distinct POS series
  trend: '#22c55e', // --success
} as const;

export const tooltipStyle = {
  backgroundColor: '#0f172a', // --card
  border: '1px solid #334155', // --border
  borderRadius: 8,
  color: '#f8fafc', // --foreground
  fontSize: 12,
} as const;

export const AXIS_PROPS = {
  stroke: CHART.axis,
  tick: { fill: CHART.axis, fontSize: 12 },
  tickLine: false,
} as const;
