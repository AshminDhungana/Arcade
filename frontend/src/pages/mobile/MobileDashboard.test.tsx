import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MobileDashboard } from './MobileDashboard'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

const mockAnalytics = {
  revenueToday: 125000,
  activeSessions: 8,
  shiftSummary: { revenue: 125000, sessions: 12, avgDuration: 45 },
  topZones: [
    { zoneId: 'zone-1', name: 'VIP Zone', revenue: 50000, utilization: 0.8 },
    { zoneId: 'zone-2', name: 'Main Floor', revenue: 45000, utilization: 0.6 },
    { zoneId: 'zone-3', name: 'Console Corner', revenue: 30000, utilization: 0.4 },
  ],
  activeSessionsList: [
    { id: 'sess-1', seatName: 'PC-01', zoneName: 'VIP Zone', memberName: 'John', startTime: new Date().toISOString(), duration: 1800, status: 'IN_USE' },
    { id: 'sess-2', seatName: 'PS5-01', zoneName: 'Console Corner', memberName: undefined, startTime: new Date().toISOString(), duration: 3600, status: 'PAUSED' },
  ],
}

vi.mock('@/hooks/useAnalytics', () => ({
  useAnalytics: () => ({ data: mockAnalytics, refetch: vi.fn() }),
}))

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ subscribe: vi.fn(() => vi.fn()) }),
}))

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/mobile']}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

test('renders 4 stat cards in grid', async () => {
  render(<MobileDashboard />, { wrapper: makeWrapper() })
  await waitFor(() => {
    expect(screen.getByTestId('stat-revenue')).toHaveTextContent('Rs. 1250.00')
    expect(screen.getByTestId('stat-sessions')).toHaveTextContent('8')
    expect(screen.getByTestId('stat-shift-revenue')).toHaveTextContent('Rs. 1250.00')
    expect(screen.getByTestId('stat-shift-sessions')).toHaveTextContent('12')
  })
})

test('renders top zones list', async () => {
  render(<MobileDashboard />, { wrapper: makeWrapper() })
  await waitFor(() => {
    expect(screen.getAllByText('VIP Zone')).toHaveLength(2)
    expect(screen.getAllByText('Main Floor')).toHaveLength(1)
    expect(screen.getAllByText('Console Corner')).toHaveLength(2)
  })
})
