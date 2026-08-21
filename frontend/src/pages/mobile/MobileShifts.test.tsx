import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MobileShifts } from './MobileShifts'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

const mockShiftData = {
  isOpen: true,
  shift: { id: 'shift-1', openedAt: new Date().toISOString(), openedBy: 'Admin User' },
  summary: { revenue: 125000, sessions: 12, avgDuration: 45, posRevenue: 25000 },
}

vi.mock('@/hooks/useShift', () => ({
  useShift: () => ({ data: mockShiftData, refetch: vi.fn(), openShift: vi.fn(), closeShift: vi.fn() }),
}))

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ subscribe: vi.fn(() => vi.fn()) }),
}))

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/mobile/shifts']}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

test('renders shift status as open with summary', async () => {
  render(<MobileShifts />, { wrapper: makeWrapper() })
  await waitFor(() => {
    expect(screen.getByText('Shift Open')).toBeInTheDocument()
    expect(screen.getByText('Rs. 1250.00')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
  })
})

test('shows close shift button when shift is open', async () => {
  render(<MobileShifts />, { wrapper: makeWrapper() })
  await waitFor(() => {
    expect(screen.getByRole('button', { name: /close shift/i })).toBeInTheDocument()
  })
})
