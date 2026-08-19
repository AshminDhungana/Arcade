/** POS-domain type definitions.
 *  Mirror backend schemas from `backend/schemas/pos.py`. */

/** Menu item as returned by `GET /api/pos/menu`. */
export interface MenuItem {
  id: string;
  name: string;
  category: string | null;
  price_paise: number;
  stock_quantity: number | null;
  low_stock_threshold: number | null;
  is_available: boolean;
  created_at: string;
  updated_at: string;
}

/** A POS item attached to a session, as returned by `GET /api/pos/items/{sessionId}`. */
export interface SessionPOSItem {
  id: string;
  session_id: string;
  menu_item_id: string;
  quantity: number;
  unit_price_paise: number;
  added_at: string;
}

/** Feature flags extracted from `GET /api/settings`.
 *  All flags default to `false` if missing from the backend response. */
export interface FeatureFlags {
  // Core Features
  enable_members: boolean;
  enable_packages: boolean;
  enable_pos: boolean;
  enable_reservations: boolean;
  enable_wake_on_lan: boolean;
  // Operations
  enable_inventory: boolean;
  enable_vouchers: boolean;
  enable_tournaments: boolean;
  enable_expense_tracking: boolean;
  enable_health_monitoring: boolean;
  enable_remote_commands: boolean;
  enable_analytics: boolean;
  enable_promotions: boolean;
  enable_maintenance_mode: boolean;
  // Agent/Overlay
  enable_tuya: boolean;
  enable_kiosk_branding: boolean;
  overlay_pauses_billing: boolean;
  require_member_for_session: boolean;
  enable_assigned_time_limit: boolean;
  // Advanced
  require_print_before_release: boolean;
  block_shift_close_unprinted: boolean;
  enable_loyalty_discounts: boolean;
  enable_audit_export: boolean;
}

/** Full app settings from `GET /api/settings` — includes both feature flags and config values. */
export interface AppSettings {
  // Feature flags (boolean)
  enable_members: boolean;
  enable_packages: boolean;
  enable_pos: boolean;
  enable_inventory: boolean;
  enable_reservations: boolean;
  enable_vouchers: boolean;
  enable_tournaments: boolean;
  enable_expense_tracking: boolean;
  enable_health_monitoring: boolean;
  require_member_for_session: boolean;
  enable_tuya: boolean;
  require_print_before_release: boolean;
  block_shift_close_unprinted: boolean;
  overlay_pauses_billing: boolean;
  enable_assigned_time_limit: boolean;
  enable_wake_on_lan: boolean;
  enable_remote_commands: boolean;
  enable_analytics: boolean;
  enable_promotions: boolean;
  enable_loyalty_discounts: boolean;
  enable_maintenance_mode: boolean;
  enable_kiosk_branding: boolean;
  enable_audit_export: boolean;
  // Config values (numbers/strings)
  shift_cash_variance_threshold: number;
  // Add other config values here as needed
}
