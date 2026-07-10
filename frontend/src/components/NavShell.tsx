import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, Settings as SettingsIcon } from 'lucide-react';
import { useFeatureFlagStore } from '@/store/featureFlagStore';
import type { ReactNode } from 'react';

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, flag: null },
  { to: '/members', label: 'Members', icon: Users, flag: 'enable_members' as const },
  { to: '/settings', label: 'Settings', icon: SettingsIcon, flag: null },
];

export function NavShell({ children }: { children: ReactNode }) {
  const flags = useFeatureFlagStore((s) => s.flags);
  const items = NAV.filter((n) => !n.flag || flags[n.flag]);
  return (
    <div className="flex min-h-screen bg-slate-900">
      <aside className="w-60 shrink-0 border-r border-slate-700 bg-slate-800 p-3">
        <h1 className="px-3 py-2 text-lg font-bold text-white">Arcade</h1>
        <nav className="flex flex-col gap-1">
          {items.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-700'
                }`
              }
            >
              <n.icon className="h-4 w-4" />
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1">{children}</div>
    </div>
  );
}
