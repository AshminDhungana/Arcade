// frontend/src/components/invoice/InvoiceLineItem.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InvoiceLineItem } from './InvoiceLineItem';

const mockItem = {
  id: '1',
  invoice_id: 'inv_1',
  type: 'TIME_CHARGE' as const,
  description: 'Time charge',
  quantity: 60,
  unit_price_paise: 200,
  total_paise: 12000,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('InvoiceLineItem', () => {
  it('renders description, quantity, unit price, and total', () => {
    render(<InvoiceLineItem item={mockItem} />);
    expect(screen.getByText('Time charge')).toBeInTheDocument();
    expect(screen.getByText('x60')).toBeInTheDocument();
    expect(screen.getByText('Rs. 2.00')).toBeInTheDocument(); // unit price
    expect(screen.getByText('Rs. 120.00')).toBeInTheDocument(); // total
  });

  it('applies discount styling for discount types', () => {
    const discountItem = { ...mockItem, type: 'DISCOUNT' as const, total_paise: -500 };
    render(<InvoiceLineItem item={discountItem} />);
    const row = screen.getByText('Time charge').closest('tr');
    expect(row).toHaveClass('text-red-400');
  });

  it('applies package credit styling', () => {
    const pkgItem = { ...mockItem, type: 'PACKAGE_CREDIT' as const, total_paise: 3000 };
    render(<InvoiceLineItem item={pkgItem} />);
    const row = screen.getByText('Time charge').closest('tr');
    expect(row).toHaveClass('text-emerald-400');
  });
});
