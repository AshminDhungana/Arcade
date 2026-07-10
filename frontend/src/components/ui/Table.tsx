import type { ReactNode, ThHTMLAttributes, TdHTMLAttributes } from 'react';

export function Table({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`overflow-hidden rounded-lg border border-slate-700/50 ${className}`}>
      <table className="min-w-full divide-y divide-slate-700/50">{children}</table>
    </div>
  );
}
export const Th = (p: ThHTMLAttributes<HTMLTableCellElement>) => (
  <th {...p} className={`px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-slate-400 ${p.className ?? ''}`} />
);
export const Td = (p: TdHTMLAttributes<HTMLTableCellElement>) => (
  <td {...p} className={`px-3 py-2 text-sm text-slate-200 ${p.className ?? ''}`} />
);
