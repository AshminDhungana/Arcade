// frontend/src/components/invoice/InvoicePanel.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InvoicePanel } from './InvoicePanel';
import type { Invoice } from '@/types/invoice';

const mockInvoice: Invoice = {
  id: 'inv_1',
  session_id: 'sess_1',
  member_id: 'member_1',
  shift_id: 'shift_1',
  time_charge_paise: 25000,
  package_credit_used_paise: 10000,
  discount_paise: 5000,
  pos_total_paise: 8000,
  total_paise: 18000, // 25000 + 8000 - 10000 - 5000
  payment_method: 'CASH',
  created_at: new Date().toISOString(),
  line_items: [
    {
      id: 'li_1',
      invoice_id: 'inv_1',
      type: 'TIME_CHARGE',
      description: 'Time Charge (PER_MINUTE)',
      quantity: 125,
      unit_price_paise: 200,
      total_paise: 25000,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'li_2',
      invoice_id: 'inv_1',
      type: 'PACKAGE_CREDIT',
      description: 'Package Drawdown',
      quantity: 50,
      unit_price_paise: 200,
      total_paise: 10000,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'li_3',
      invoice_id: 'inv_1',
      type: 'POS_ITEM',
      description: 'Cola',
      quantity: 2,
      unit_price_paise: 4000,
      total_paise: 8000,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ],
};

describe('InvoicePanel', () => {
  it('renders duration when sessionDurationSeconds is provided', () => {
    render(<InvoicePanel invoice={mockInvoice} sessionDurationSeconds={7500} />);
    expect(screen.getByText('Duration')).toBeInTheDocument();
    expect(screen.getByText('2h 5m')).toBeInTheDocument(); // 7500s = 2h 5m
  });

  it('renders receipt line items inside a table', () => {
    render(<InvoicePanel invoice={mockInvoice} />);
    expect(screen.getByText('Time Charge (PER_MINUTE)')).toBeInTheDocument();
    expect(screen.getByText('Package Drawdown')).toBeInTheDocument();
    expect(screen.getByText('Cola')).toBeInTheDocument();
  });

  it('renders subtotals, package credit, discount and grand total', () => {
    render(<InvoicePanel invoice={mockInvoice} />);
    expect(screen.getByText('Time Charge')).toBeInTheDocument();
    expect(screen.getAllByText('Rs. 250.00').length).toBe(2);

    expect(screen.getByText('Package Credit Applied')).toBeInTheDocument();
    expect(screen.getByText('Rs. 100.00')).toBeInTheDocument(); // in table row
    expect(screen.getByText('-Rs. 100.00')).toBeInTheDocument(); // in summary totals

    expect(screen.getByText('Discounts')).toBeInTheDocument();
    expect(screen.getByText('-Rs. 50.00')).toBeInTheDocument();

    expect(screen.getByText('POS items total')).toBeInTheDocument();
    expect(screen.getAllByText('Rs. 80.00').length).toBe(2);

    expect(screen.getByText('Grand Total')).toBeInTheDocument();
    expect(screen.getByText('Rs. 180.00')).toBeInTheDocument();
  });

  it('renders payment method badge', () => {
    render(<InvoicePanel invoice={mockInvoice} />);
    expect(screen.getByText('Cash Paid')).toBeInTheDocument();
  });
});
