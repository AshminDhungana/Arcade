import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KpiRow } from './KpiRow';
import type { AnalyticsSummary } from '@/types/analytics';

const summary: AnalyticsSummary = {
  total_revenue_paise: 25050,
  session_count: 12,
  average_duration_seconds: 4980, // 1h 23m
  busiest_hour: { hour: 15, session_count: 3 },
  weekly_revenue: [],
  top_pos_items: [],
  zone_utilisation: [],
  member_registration_trend: [],
  member_stats: { new_today: 0, active_last_30d: 0, top_spenders: [] },
  health_alerts: [],
  upcoming_reservations: [],
  wol_success_rates: [],
  current_shift_id: null,
  shift_opened_at: null,
};

describe('KpiRow', () => {
  it('renders all four KPIs formatted', () => {
    render(<KpiRow summary={summary} />);
    expect(screen.getByText('Rs. 250.50')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('1h 23m')).toBeInTheDocument();
    expect(screen.getByText('3 PM')).toBeInTheDocument();
  });

  it('shows an em dash when there is no busiest hour', () => {
    render(<KpiRow summary={{ ...summary, busiest_hour: null }} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });
});
