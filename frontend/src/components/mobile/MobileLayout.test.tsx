import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MobileLayout } from './MobileLayout'

vi.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    accessToken: 'test-token',
    staff: { id: 'staff-1', name: 'Test Admin', role: 'ADMIN', is_active: true },
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    clear: vi.fn(),
  }),
}))

function renderWithRouter(ui: React.ReactElement) {
  return render(
    <BrowserRouter>
      {ui}
    </BrowserRouter>
  )
}

test('renders header with cafe name and logout button', () => {
  renderWithRouter(
    <MobileLayout>
      <div data-testid="child-content">Child</div>
    </MobileLayout>
  )
  expect(screen.getByTestId('mobile-header')).toBeInTheDocument()
  expect(screen.getByText('Test Admin')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
})

test('renders bottom tab bar with 4 tabs', () => {
  renderWithRouter(
    <MobileLayout>
      <div data-testid="child-content">Child</div>
    </MobileLayout>
  )
  const tabs = screen.getAllByRole('tab')
  expect(tabs).toHaveLength(4)
  expect(tabs[0]).toHaveTextContent(/dashboard/i)
  expect(tabs[1]).toHaveTextContent(/sessions/i)
  expect(tabs[2]).toHaveTextContent(/shifts/i)
  expect(tabs[3]).toHaveTextContent(/settings/i)
})
