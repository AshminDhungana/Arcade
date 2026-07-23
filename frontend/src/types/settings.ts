import type { PricingModel } from './session';

export type { PricingModel };

export interface Zone {
  id: string;
  name: string;
  rate_per_minute_paise: number;
  rate_per_hour_paise: number;
  pricing_model: PricingModel;
  block_minutes: number | null;
}

export interface DeviceType {
  id: string;
  name: string;
  description: string | null;
}

export interface PeakSchedule {
  id: string;
  name: string;
  is_peak: boolean;
  day_of_week: number | null; // 0-6, null=all
  start_time: string; // "HH:MM"
  end_time: string; // "HH:MM"
  surcharge_paise: number; // per hour
}

export type StaffRole = 'ADMIN' | 'CASHIER';

export interface Staff {
  id: string;
  name: string;
  role: StaffRole;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface StaffZone {
  zone_id: string;
  zone_name: string;
  granted_by: string;
  granted_at: string;
  is_active: boolean;
}

export interface StaffZoneAssign {
  zone_id: string;
}

export interface StaffZoneBulkAssign {
  zone_ids: string[];
}

// Request types for API
export type StaffZoneAssignRequest = StaffZoneAssign;
export type StaffZoneBulkAssignRequest = StaffZoneBulkAssign;

export interface MenuItem {
  id: string;
  name: string;
  category: string | null;
  price_paise: number;
  stock_quantity: number | null;
  low_stock_threshold: number | null;
  is_available: boolean;
}

export type SeatStatus =
  | 'AVAILABLE'
  | 'IN_USE'
  | 'RESERVED'
  | 'PAUSED'
  | 'MAINTENANCE'
  | 'OFFLINE'
  | 'BOOTING'
  | 'UNREACHABLE'
  | 'EXPIRED';

export interface SeatFormData {
  name: string;
  zone_id: string;
  mac_address: string;
  plug_id: string;
  is_console: boolean;
  notes: string;
}

export interface Seat {
  id: string;
  name: string;
  zone_id: string;
  zone_name?: string;
  mac_address: string | null;
  status: string;
  plug_id: string | null;
  is_console: boolean;
  notes: string | null;
  overlay_forced: boolean;
  assigned_end_at: string | null;
  wol_attempts: number;
  wol_successes: number;
  wol_failures: number;
  current_session_id?: string;
  current_session_started_at?: string;
  created_at: string;
  updated_at: string;
}

export interface SeatCreate {
  name: string;
  zone_id: string;
  mac_address?: string | null;
  plug_id?: string | null;
  is_console?: boolean;
  notes?: string | null;
}

export interface SeatUpdate {
  name?: string;
  zone_id?: string;
  mac_address?: string | null;
  plug_id?: string | null;
  is_console?: boolean;
  notes?: string | null;
}
