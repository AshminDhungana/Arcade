import { describe, it, expect, beforeAll } from 'vitest';
import { render } from '@testing-library/react';
import { RevenueBarChart } from './RevenueBarChart';
import { installChartLayoutMocks } from './analyticsTestUtils';
import type { DailyRevenue } from '@/types/analytics';

beforeAll(() => installChartLayoutMocks());

const data: DailyRevenue[] = [
  { date: '2026-07-13', total_paise: 10000 }, // Mon
  { date: '2026-07-14', total_paise: 20000 }, // Tue
  { date: '2026-07-15', total_paise: 5000 }, // Wed
];

describe('RevenueBarChart', () => {
  it('renders an svg with one bar per day bound to the data', () => {
    const { container } = render(<RevenueBarChart data={data} />);
    expect(container.querySelector('svg')).toBeTruthy();
    expect(container.querySelectorAll('.recharts-bar-rectangle')).toHaveLength(data.length);
  });
});
