import { Outlet, useLocation } from 'react-router-dom'
import { BottomTabBar } from './BottomTabBar'
import { useAuthStore } from '@/store/authStore'

export function MobileLayout() {
  const { staff, logout } = useAuthStore()
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col" data-testid="mobile-layout">
      <header className="bg-white border-b border-gray-200 px-4 py-3 sticky top-0 z-10" data-testid="mobile-header">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold text-gray-900">{staff?.name || 'Arcade'}</h1>
          <button
            onClick={logout}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            data-testid="mobile-logout"
          >
            Logout
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-auto pb-16">
        <div className="max-w-screen-md mx-auto px-4 py-4">
          <Outlet />
        </div>
      </main>

      <BottomTabBar currentPath={location.pathname} />
    </div>
  )
}
