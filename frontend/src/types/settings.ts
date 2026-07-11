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

export interface MenuItem {
  id: string;
  name: string;
  category: string | null;
  price_paise: number;
  stock_quantity: number | null;
  low_stock_threshold: number | null;
  is_available: boolean;
}
