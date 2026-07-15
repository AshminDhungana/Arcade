import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HealthAlerts } from './HealthAlerts';
import { SeatStatus } from '@/types/seat';
import type { Seat } from '@/types/seat';
import type { HealthAlert } from '@/types/analytics';

const seat = (id: string, name: string, status: SeatStatus): Seat => ({
  id,
  name,
  zone_id: 'z',
  mac_address: null,
  status,
  plug_id: null,
  is_console: false,
  notes: null,
  wol_attempts: 0,
  wol_successes: 0,
  wol_failures: 0,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
});

const alerts: HealthAlert[] = [
  { seat_id: 's1', seat_name: 'PC-01', reasons: ['cpu_temp_red'] },
  { seat_id: 's2', seat_name: 'PC-02', reasons: ['no_health_report'] },
];

describe('HealthAlerts', () => {
  it('merges summary health alerts with offline seats', () => {
    const seats = [
      seat('s1', 'PC-01', SeatStatus.AVAILABLE),
      seat('s3', 'PC-03', SeatStatus.OFFLINE),
      seat('s4', 'PC-04', SeatStatus.UNREACHABLE),
    ];
    render(<HealthAlerts alerts={alerts} seats={seats} />);
    expect(screen.getByText(/Overheating: PC-01/)).toBeInTheDocument();
    expect(screen.getByText(/No health report: PC-02/)).toBeInTheDocument();
    expect(screen.getByText(/Offline: PC-03/)).toBeInTheDocument();
    expect(screen.getByText(/Offline: PC-04/)).toBeInTheDocument();
  });

  it('shows an all-clear message when there are no alerts', () => {
    render(<HealthAlerts alerts={[]} seats={[seat('s1', 'PC-01', SeatStatus.AVAILABLE)]} />);
    expect(screen.getByText(/All seats healthy/i)).toBeInTheDocument();
  });
});
