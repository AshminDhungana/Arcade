import type { ReactNode } from 'react';

export interface TabItem {
  id: string;
  label: string;
  icon?: ReactNode;
}

interface TabsProps {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
}

export function Tabs({ tabs, active, onChange }: TabsProps) {
  return (
    <nav
      className="flex gap-1 overflow-x-auto border-b border-slate-700 bg-slate-800/50 px-2"
      role="tablist"
      aria-label="Sections"
    >
      {tabs.map((t) => (
        <button
          key={t.id}
          role="tab"
          aria-selected={active === t.id}
          type="button"
          onClick={() => onChange(t.id)}
          className={`flex shrink-0 items-center gap-2 whitespace-nowrap border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
            active === t.id
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          {t.icon}
          {t.label}
        </button>
      ))}
    </nav>
  );
}
