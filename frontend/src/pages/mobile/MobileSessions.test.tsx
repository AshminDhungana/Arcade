import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MobileSessions } from './MobileSessions'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

const mockSessions = [
  { id: 'sess-1', seatName: 'PC-01', zoneName: 'VIP Zone', memberName: 'John', startTime: new Date().toISOString(), duration: 1800, status: 'IN_USE' },
  { id: 'sess-2', seatName: 'PS5-01', zoneName: 'Console Corner', memberName: undefined, startTime: new Date().toISOString(), duration: 3600, status: 'PAUSED' },
  { id: 'sess-3', seatName: 'PC-02', zoneName: 'Main Floor', memberName: 'Jane', startTime: new Date().toISOString(), duration: 900, status: 'IN_USE' },
]

vi.mock('@/hooks/useSessions', () => ({
  useSessions: () => ({ data: mockSessions, refetch: vi.fn() }),
}))

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ subscribe: vi.fn(() => vi.fn()) }),
}))

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/mobile/sessions']}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

test('renders session list with all sessions', async () => {
  render(<MobileSessions />, { wrapper: makeWrapper() })
  await waitFor(() => {
    expect(screen.getByText('PC-01')).toBeInTheDocument()
    expect(screen.getByText('PS5-01')).toBeInTheDocument()
    expect(screen.getByText('PC-02')).toBeInTheDocument()
  })
})

test('opens detail modal when session is tapped', async () => {
  render(<MobileSessions />, { wrapper: makeWrapper() })
  await waitFor(() => {
    expect(screen.getByTestId('mobile-session-list')).toBeInTheDocument()
  })
  // Click on the first session list item (which has role="button")
  const sessionButtons = screen.getAllByRole('button', { name: /PC-01/ })
  fireEvent.click(sessionButtons[0])
  await waitFor(() => {
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByTestId('session-detail-modal')).toBeInTheDocument()
  })
})

test('filters sessions by zone', async () => {
  render(<MobileSessions />, { wrapper: makeWrapper() })
  await waitFor(() => {
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })
  const select = screen.getByRole('combobox')
  fireEvent.change(select, { target: { value: 'VIP Zone' } })
  await waitFor(() => {
    expect(screen.getByText('PC-01')).toBeInTheDocument()
    expect(screen.queryByText('PS5-01')).not.toBeInTheDocument()
  })
})
