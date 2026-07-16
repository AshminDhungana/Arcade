import { NavLink } from 'react-router-dom';
import { useState } from 'react';
import { LayoutDashboard, Users, BarChart3, Settings as SettingsIcon, CalendarDays, Menu, X } from 'lucide-react';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import type { ReactNode } from 'react';

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, flag: null },
  { to: '/members', label: 'Members', icon: Users, flag: 'enable_members' as const },
  { to: '/analytics', label: 'Analytics', icon: BarChart3, flag: null },
  { to: '/events', label: 'Events', icon: CalendarDays, flag: 'enable_tournaments' as const },
  { to: '/settings', label: 'Settings', icon: SettingsIcon, flag: null },
];

export function NavShell({ children }: { children: ReactNode }) {
  const flags = useFeatureFlagStore((s) => s.flags);
  const items = NAV.filter((n) => !n.flag || flags[n.flag]);
  const [menuOpen, setMenuOpen] = useState(false);

  const navLinks = (
    <nav className="flex flex-col gap-1" aria-label="Primary">
      {items.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          end={n.to === '/'}
          onClick={() => setMenuOpen(false)}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium min-h-11 ${
              isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-700'
            }`
          }
        >
          <n.icon className="h-4 w-4" />
          {n.label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-slate-900 md:flex">
      {/* Desktop sidebar (md and up) */}
      <aside className="hidden md:flex md:w-60 md:shrink-0 md:flex-col border-r border-slate-700 bg-slate-800 p-3">
        <h1 className="px-3 py-2 text-lg font-bold text-white">Arcade</h1>
        {navLinks}
      </aside>

      {/* Mobile top bar (below md) */}
      <div className="flex items-center justify-between border-b border-slate-700 bg-slate-800 px-4 py-3 sticky top-0 z-30 md:hidden">
        <h1 className="text-lg font-bold text-white">Arcade</h1>
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          aria-label="Open menu"
          aria-expanded={menuOpen}
          className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-300 hover:bg-slate-700"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>

      {/* Mobile slide-in drawer */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMenuOpen(false)}
            aria-hidden="true"
          />
          <aside className="absolute left-0 top-0 flex h-full w-60 max-w-[80%] flex-col bg-slate-800 p-3">
            <div className="flex items-center justify-between mb-2">
              <h1 className="px-3 py-2 text-lg font-bold text-white">Arcade</h1>
              <button
                type="button"
                onClick={() => setMenuOpen(false)}
                aria-label="Close menu"
                className="flex h-11 w-11 items-center justify-center rounded-lg text-slate-300 hover:bg-slate-700"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            {navLinks}
          </aside>
        </div>
      )}

      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
