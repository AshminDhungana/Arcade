import { PaymentMethod } from './invoice';

export type PricingModel = 'PER_MINUTE' | 'FLAT_HOURLY' | 'TIME_BLOCK';

export type SessionStatus = 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'ABANDONED';

export interface SessionResponse {
  id: string;
  seat_id: string;
  member_id: string | null;
  shift_id: string | null;
  status: SessionStatus;
  started_at: string; // ISO datetime
  ended_at: string | null; // ISO datetime
  paused_at: string | null; // ISO datetime
  total_paused_seconds: number;
  locked_rate_paise: number;
  locked_pricing_model: PricingModel;
  package_entitlement_id: string | null;
  promotion_id: string | null;
  discount_paise: number;
  payment_method: PaymentMethod | null;
  created_at: string;
  updated_at: string;
}
