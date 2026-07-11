export type MemberTier = 'BRONZE' | 'SILVER' | 'GOLD';

export interface Member {
  id: string;
  name: string;
  phone: string;
  birth_month: number | null;
  wallet_balance_paise: number;
  loyalty_points: number;
  tier: MemberTier;
  total_visits: number;
  total_seconds_played: number;
  created_at: string; // ISO datetime
  updated_at: string;
}

export type PackageType = 'HOUR_BUNDLE' | 'DAY_PASS' | 'NIGHT_PASS' | 'MONTHLY';
export type EntitlementStatus = 'ACTIVE' | 'EXHAUSTED' | 'EXPIRED';

export interface Package {
  id: string;
  name: string;
  type: PackageType;
  total_minutes: number;
  price_paise: number;
  valid_days: number | null;
  zone_restriction_id: string | null;
  is_active: boolean;
}

export interface MemberPackageEntitlement {
  id: string;
  member_id: string;
  package_id: string;
  remaining_minutes: number;
  expires_at: string | null;
  status: EntitlementStatus;
  purchased_at: string;
  updated_at: string;
}

export interface WalletTransaction {
  member_id: string;
  type: string; // TOPUP | PACKAGE_PURCHASE | ...
  amount_paise: number; // signed
  balance_after_paise: number;
  payment_method: string;
  staff_id: string | null;
  reference_id: string | null;
  created_at: string; // ISO datetime
}
