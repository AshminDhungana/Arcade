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
  require_print_before_release: boolean;
}
