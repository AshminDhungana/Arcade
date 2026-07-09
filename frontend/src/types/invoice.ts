/** Mirrors backend `backend/schemas/invoice.py` — do not diverge. */

export type PaymentMethod = 'CASH' | 'WALLET' | 'CARD' | 'PACKAGE';

export type InvoiceLineItemType =
  | 'TIME_CHARGE'
  | 'PACKAGE_CREDIT'
  | 'POS_ITEM'
  | 'DISCOUNT'
  | 'PROMOTION_DISCOUNT'
  | 'LOYALTY_DISCOUNT';

export interface InvoiceLineItem {
  id: string;
  invoice_id: string;
  type: InvoiceLineItemType;
  description: string;
  quantity: number;
  unit_price_paise: number;
  total_paise: number;
  created_at: string;
  updated_at: string;
}

export interface Invoice {
  id: string;
  session_id: string;
  member_id: string | null;
  shift_id: string | null;
  time_charge_paise: number;
  package_credit_used_paise: number;
  discount_paise: number;
  pos_total_paise: number;
  total_paise: number;
  payment_method: PaymentMethod;
  created_at: string;
  line_items: InvoiceLineItem[];
}
