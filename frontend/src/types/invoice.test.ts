// frontend/src/types/invoice.test.ts
import { describe, it, expect } from 'vitest';
import type { Invoice, InvoiceLineItem, PaymentMethod } from './invoice';

describe('Invoice types', () => {
  it('should compile PaymentMethod enum', () => {
    const method: PaymentMethod = 'CASH';
    expect(method).toBe('CASH');
  });

  it('should compile InvoiceLineItem structure', () => {
    const item: InvoiceLineItem = {
      id: '1',
      invoice_id: 'inv_1',
      type: 'TIME_CHARGE',
      description: 'Time charge',
      quantity: 60,
      unit_price_paise: 200,
      total_paise: 12000,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    expect(item.total_paise).toBe(12000);
  });

  it('should compile Invoice structure', () => {
    const invoice: Invoice = {
      id: 'inv_1',
      session_id: 'sess_1',
      member_id: null,
      shift_id: null,
      time_charge_paise: 10000,
      package_credit_used_paise: 0,
      discount_paise: 500,
      pos_total_paise: 2500,
      total_paise: 12000,
      payment_method: 'CASH',
      created_at: new Date().toISOString(),
      line_items: [],
    };
    expect(invoice.total_paise).toBe(12000);
  });
});
