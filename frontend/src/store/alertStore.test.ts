import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/lib/chime', () => ({ playStaffAlertChime: vi.fn() }));

import { playStaffAlertChime } from '@/lib/chime';
import { useAlertStore } from './alertStore';

const makeAlert = () => ({
  type: 'STAFF_ALERT' as const,
  seat_id: 'seat-1',
  message: 'Staff assistance requested',
  timestamp: '2026-08-08T10:00:00Z',
});

describe('alertStore', () => {
  beforeEach(() => {
    useAlertStore.setState({ alerts: [] });
    vi.mocked(playStaffAlertChime).mockClear();
  });

  it('appends alerts to the queue in FIFO order and plays the chime', () => {
    useAlertStore.getState().push(makeAlert());
    useAlertStore.getState().push({ ...makeAlert(), seat_id: 'seat-2' });

    const { alerts } = useAlertStore.getState();
    expect(alerts).toHaveLength(2);
    expect(alerts[0].seat_id).toBe('seat-1');
    expect(alerts[1].seat_id).toBe('seat-2');
    expect(playStaffAlertChime).toHaveBeenCalledTimes(2);
  });

  it('dismiss removes the head and reveals the next alert', () => {
    useAlertStore.getState().push(makeAlert());
    useAlertStore.getState().push({ ...makeAlert(), seat_id: 'seat-2' });

    useAlertStore.getState().dismiss();

    const { alerts } = useAlertStore.getState();
    expect(alerts).toHaveLength(1);
    expect(alerts[0].seat_id).toBe('seat-2');
  });

  it('dismiss on an empty queue is a no-op', () => {
    useAlertStore.getState().dismiss();
    expect(useAlertStore.getState().alerts).toHaveLength(0);
  });
});
