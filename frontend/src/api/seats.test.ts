import { describe, it, expect } from 'vitest';
import type { Seat } from '@/types/seat';
import { SeatStatus } from '@/types/seat';

describe('Seat types', () => {
  it('Seat interface compiles with required fields', () => {
    const seat: Seat = {
      id: 'seat-001',
      name: 'PC-01',
      zone_id: 'zone-001',
      mac_address: 'aa:bb:cc:dd:ee:ff',
      status: SeatStatus.AVAILABLE,
      plug_id: null,
      is_console: false,
      notes: null,
      overlay_forced: false,
      assigned_end_at: null,
      wol_attempts: 0,
      wol_successes: 0,
      wol_failures: 0,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };
    expect(seat.status).toBe('AVAILABLE');
  });
});

describe('fetchSeats', () => {
  it('should be defined', async () => {
    const { fetchSeats } = await import('./seats');
    expect(typeof fetchSeats).toBe('function');
  });
});

describe('useSeats', () => {
  it('should be defined', async () => {
    const { useSeats } = await import('./seats');
    expect(typeof useSeats).toBe('function');
  });
});

describe('useSeat', () => {
  it('should be defined', async () => {
    const { useSeat } = await import('./seats');
    expect(typeof useSeat).toBe('function');
  });
});
