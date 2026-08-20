import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AutoStartToggle } from './AutoStartToggle';

vi.mock('../store/authStore', () => ({
  useAuthStore: () => ({
    user: { id: '1', role: 'ADMIN', staff_id: 'admin' },
  }),
}));

vi.mock('../store/featureFlagStore', () => ({
  useFeatureFlagStore: () => ({
    isEnabled: (flag: string) => flag === 'agent_auto_start',
  }),
}));

global.fetch = vi.fn();

describe('AutoStartToggle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetch).mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });
    localStorage.setItem('access_token', 'test-token');
  });

  it('renders toggle for admin users when feature flag enabled', () => {
    render(<AutoStartToggle seatId="seat_001" />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
    expect(screen.getByText('Auto-Start on Boot')).toBeInTheDocument();
  });

  it('calls API when toggled on', async () => {
    render(<AutoStartToggle seatId="seat_001" />);
    const toggle = screen.getByRole('switch');
    fireEvent.click(toggle);
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/seats/seat_001/auto-start',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ enabled: true }),
        })
      );
    });
  });

  it('calls API with enabled=false when toggled off', async () => {
    render(<AutoStartToggle seatId="seat_001" />);
    const toggle = screen.getByRole('switch');
    fireEvent.click(toggle); // on
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/seats/seat_001/auto-start',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ enabled: true }),
        })
      );
    });
    // Click again to toggle off
    fireEvent.click(toggle);
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledTimes(2);
      const calls = vi.mocked(fetch).mock.calls;
      const lastCall = calls[calls.length - 1];
      expect(lastCall[0]).toBe('/api/seats/seat_001/auto-start');
      expect(lastCall[1]).toEqual(expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ enabled: false }),
      }));
    });
  });
});
