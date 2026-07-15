import { describe, it, expect, beforeAll } from 'vitest';
import { render } from '@testing-library/react';
import { MemberTrendChart } from './MemberTrendChart';
import { installChartLayoutMocks } from './analyticsTestUtils';
import type { DailyCount } from '@/types/analytics';

beforeAll(() => installChartLayoutMocks());

const data: DailyCount[] = [
  { date: '2026-07-13', count: 2 }, // Mon
  { date: '2026-07-14', count: 0 }, // Tue
  { date: '2026-07-15', count: 1 }, // Wed
];

describe('MemberTrendChart', () => {
  it('renders an svg with a line curve and one dot per day bound to the data', () => {
    const { container } = render(<MemberTrendChart data={data} />);
    expect(container.querySelector('svg')).toBeTruthy();
    expect(container.querySelector('.recharts-line-curve')).toBeTruthy();
    expect(container.querySelectorAll('.recharts-dot')).toHaveLength(data.length);
  });
});
