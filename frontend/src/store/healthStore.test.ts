import { describe, it, expect } from 'vitest';
import { useHealthStore } from './healthStore';

describe('healthStore', () => {
  it('stores health metrics by seat_id', () => {
    const data = {
      seat_id: 'seat_001',
      cpu_pct: 45.5,
      ram_pct: 62.0,
      cpu_temp: 42,
      disk_used_gb: 120,
      disk_total_gb: 500,
      timestamp: '2026-01-01T10:00:00Z',
    };

    useHealthStore.getState().setHealth('seat_001', data);

    expect(useHealthStore.getState().getSeatHealth('seat_001')).toEqual(data);
  });

  it('returns undefined for unknown seat', () => {
    expect(useHealthStore.getState().getSeatHealth('nonexistent')).toBeUndefined();
  });
});
