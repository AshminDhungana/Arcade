export interface ShiftResponse {
  id: string;
  opened_by_staff_id: string;
  closed_by_staff_id: string | null;
  opened_at: string;
  closed_at: string | null;
  float_paise: number;
  counted_paise: number | null;
  status: 'OPEN' | 'CLOSED';
}

export interface ShiftCurrentResponse {
  shift: ShiftResponse;
  session_count: number;
  total_revenue_paise: number;
  average_duration_seconds: number;
  expected_cash_paise: number;
}
