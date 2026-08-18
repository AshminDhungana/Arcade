export interface BusiestHour {
  hour: number;
  session_count: number;
}

export interface DailyRevenue {
  date: string;
  total_paise: number;
}

export interface DailyCount {
  date: string;
  count: number;
}

export interface TopPosItem {
  menu_item_id: string;
  name: string;
  quantity: number;
}

export interface ZoneUtilisation {
  zone_id: string;
  zone_name: string;
  session_hours: number;
  available_hours: number;
  utilisation_pct: number;
}

export interface TopSpender {
  member_id: string;
  name: string;
  total_paise: number;
}

export interface MemberStats {
  new_today: number;
  active_last_30d: number;
  top_spenders: TopSpender[];
}

export interface HealthAlert {
  seat_id: string;
  seat_name: string;
  reasons: string[];
}

// P&L types (K.2)
export interface PLSummary {
  period_start: string;
  period_end: string;
  session_revenue_paise: number;
  pos_revenue_paise: number;
  total_revenue_paise: number;
  expenses_by_category: Record<string, number>;
  total_expenses_paise: number;
  gross_profit_paise: number;
  net_profit_paise: number;
}

export interface PLMonthParams {
  year: number;
  month: number;
}

export interface AnalyticsSummary {
  total_revenue_paise: number;
  session_count: number;
  average_duration_seconds: number;
  busiest_hour: BusiestHour | null;
  weekly_revenue: DailyRevenue[];
  top_pos_items: TopPosItem[];
  zone_utilisation: ZoneUtilisation[];
  member_registration_trend: DailyCount[];
  member_stats: MemberStats;
  health_alerts: HealthAlert[];
  upcoming_reservations: unknown[];
  wol_success_rates: unknown[];
  current_shift_id: string | null;
  shift_opened_at: string | null;
}
