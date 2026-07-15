import type { ReactNode } from 'react';

interface ChartCardProps {
  title: string;
  description?: string;
  ariaLabel: string;
  isEmpty: boolean;
  emptyMessage?: string;
  children: ReactNode;
}

export function ChartCard({
  title,
  description,
  ariaLabel,
  isEmpty,
  emptyMessage = 'No data yet.',
  children,
}: ChartCardProps) {
  return (
    <section
      className="rounded-xl border border-slate-700 bg-slate-800 p-4"
      role="img"
      aria-label={ariaLabel}
    >
      <header className="mb-3">
        <h2 className="text-base font-medium text-white">{title}</h2>
        {description && <p className="text-sm text-slate-400">{description}</p>}
      </header>
      {isEmpty ? (
        <div className="flex h-[260px] items-center justify-center text-sm text-slate-400">
          {emptyMessage}
        </div>
      ) : (
        children
      )}
    </section>
  );
}
