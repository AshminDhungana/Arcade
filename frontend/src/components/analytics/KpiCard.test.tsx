import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { IndianRupee } from 'lucide-react';
import { KpiCard } from './KpiCard';

describe('KpiCard', () => {
  it('renders label and value', () => {
    render(<KpiCard label="Today's revenue" value="Rs. 250.50" icon={IndianRupee} />);
    expect(screen.getByText("Today's revenue")).toBeInTheDocument();
    expect(screen.getByText('Rs. 250.50')).toBeInTheDocument();
  });

  it('renders sublabel when provided', () => {
    render(<KpiCard label="Sessions" value="12" icon={IndianRupee} sublabel="Started today" />);
    expect(screen.getByText('Started today')).toBeInTheDocument();
  });
});
