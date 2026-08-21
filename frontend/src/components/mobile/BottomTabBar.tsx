import { NavLink } from 'react-router-dom'

const TABS = [
  { path: '/mobile', label: 'Dashboard', icon: '📊' },
  { path: '/mobile/sessions', label: 'Sessions', icon: '🖥️' },
  { path: '/mobile/shifts', label: 'Shifts', icon: '💰' },
  { path: '/mobile/settings', label: 'Settings', icon: '⚙️' },
] as const

export function BottomTabBar({ currentPath }: { currentPath: string }) {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-20 max-w-screen-md mx-auto"
      role="tablist"
      aria-label="Mobile navigation"
      data-testid="bottom-tab-bar"
    >
      <div className="grid grid-cols-4">
        {TABS.map((tab) => (
          <NavLink
            key={tab.path}
            to={tab.path}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center py-2 px-2 text-xs touch-target-min ${
                isActive
                  ? 'text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`
            }
            role="tab"
            aria-selected={currentPath === tab.path}
            aria-controls={`panel-${tab.label.toLowerCase()}`}
            id={`tab-${tab.label.toLowerCase()}`}
            data-testid={`tab-${tab.label.toLowerCase()}`}
          >
            <span className="text-lg" aria-hidden="true">{tab.icon}</span>
            <span>{tab.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
