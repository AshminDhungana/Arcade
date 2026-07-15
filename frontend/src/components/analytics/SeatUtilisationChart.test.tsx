import { describe, it, expect, beforeAll } from 'vitest';
import { render } from '@testing-library/react';
import { SeatUtilisationChart } from './SeatUtilisationChart';
import { installChartLayoutMocks } from './analyticsTestUtils';
import type { ZoneUtilisation } from '@/types/analytics';

beforeAll(() => installChartLayoutMocks());

const data: ZoneUtilisation[] = [
  { zone_id: 'z1', zone_name: 'Zone A', session_hours: 20, available_hours: 24, utilisation_pct: 83.33 },
  { zone_id: 'z2', zone_name: 'Zone B', session_hours: 5, available_hours: 24, utilisation_pct: 20.83 },
];

describe('SeatUtilisationChart', () => {
  it('renders an svg with one bar per zone bound to the data', () => {
    const { container } = render(<SeatUtilisationChart data={data} />);
    expect(container.querySelector('svg')).toBeTruthy();
    expect(container.querySelectorAll('.recharts-bar-rectangle')).toHaveLength(data.length);
  });
});
