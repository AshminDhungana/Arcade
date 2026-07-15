import type { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  sublabel?: string;
}

export function KpiCard({ label, value, icon: Icon, sublabel }: KpiCardProps) {
  return (
    <div className="flex min-h-[96px] flex-col justify-between rounded-xl border border-slate-700 bg-slate-800 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm text-slate-400">{label}</span>
        <Icon className="h-5 w-5 text-slate-500" aria-hidden="true" />
      </div>
      <div className="mt-2">
        <p className="text-2xl font-semibold tabular-nums text-white">{value}</p>
        {sublabel && <p className="mt-1 text-xs text-slate-400">{sublabel}</p>}
      </div>
    </div>
  );
}
