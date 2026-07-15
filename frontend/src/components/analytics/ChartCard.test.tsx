import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChartCard } from './ChartCard';

describe('ChartCard', () => {
  it('renders title and children, exposed as an image with aria-label', () => {
    render(
      <ChartCard title="Weekly revenue" ariaLabel="Weekly revenue bar chart" isEmpty={false}>
        <span>chart-body</span>
      </ChartCard>,
    );
    expect(screen.getByText('Weekly revenue')).toBeInTheDocument();
    expect(screen.getByText('chart-body')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /weekly revenue bar chart/i })).toBeInTheDocument();
  });

  it('shows empty state when isEmpty', () => {
    render(<ChartCard title="Weekly revenue" ariaLabel="x" isEmpty>{null}</ChartCard>);
    expect(screen.getByText('No data yet.')).toBeInTheDocument();
  });
});
