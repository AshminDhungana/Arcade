import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { MobileSettings } from './MobileSettings'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

const mockSettings = {
  cafeName: 'Arcade Cafe',
  timezone: 'Asia/Kolkata',
  currency: 'INR',
  autoCloseShift: false,
  sessionTimeout: 30,
  enableMembers: true,
  enableTournaments: false,
  printerEnabled: true,
  printerIp: '192.168.1.100',
}

vi.mock('@/hooks/useSettings', () => ({
  useSettings: () => ({ data: mockSettings, refetch: vi.fn(), mutate: vi.fn() }),
}))

vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({ subscribe: vi.fn(() => vi.fn()) }),
}))

const makeWrapper = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/mobile/settings']}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

test('renders settings sections', async () => {
  render(<MobileSettings />, { wrapper: makeWrapper() })
  await waitFor(() => {
    expect(screen.getByText('General')).toBeInTheDocument()
    expect(screen.getByText('Features')).toBeInTheDocument()
    expect(screen.getByText('Printer')).toBeInTheDocument()
  })
})

test('renders cafe name input', async () => {
  render(<MobileSettings />, { wrapper: makeWrapper() })
  await waitFor(() => {
    expect(screen.getByLabelText('Cafe Name')).toHaveValue('Arcade Cafe')
  })
})

test('toggles feature flags', async () => {
  render(<MobileSettings />, { wrapper: makeWrapper() })
  await waitFor(() => {
    const membersCheckbox = screen.getByLabelText(/members management/i)
    expect(membersCheckbox).toBeChecked()

    const tournamentsCheckbox = screen.getByLabelText(/tournaments/i)
    expect(tournamentsCheckbox).not.toBeChecked()
  })
})

test('shows save button', async () => {
  render(<MobileSettings />, { wrapper: makeWrapper() })
  await waitFor(() => {
    expect(screen.getByRole('button', { name: /save all settings/i })).toBeInTheDocument()
  })
})
