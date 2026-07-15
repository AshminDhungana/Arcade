import { describe, it, expect, beforeAll } from 'vitest';
import { render } from '@testing-library/react';
import { TopPosItemsChart } from './TopPosItemsChart';
import { installChartLayoutMocks } from './analyticsTestUtils';
import type { TopPosItem } from '@/types/analytics';

beforeAll(() => installChartLayoutMocks());

const data: TopPosItem[] = [
  { menu_item_id: 'm1', name: 'Tea', quantity: 10 },
  { menu_item_id: 'm2', name: 'Coffee', quantity: 4 },
];

describe('TopPosItemsChart', () => {
  it('renders an svg with one horizontal bar per item bound to the data', () => {
    const { container } = render(<TopPosItemsChart data={data} />);
    expect(container.querySelector('svg')).toBeTruthy();
    expect(container.querySelectorAll('.recharts-bar-rectangle')).toHaveLength(data.length);
  });
});
