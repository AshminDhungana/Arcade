import type { ReactNode, ThHTMLAttributes, TdHTMLAttributes } from 'react';

export function Table({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`overflow-x-auto rounded-lg border border-border ${className}`}>
      <table className="w-full text-sm">{children}</table>
    </div>
  );
}
export const Th = (p: ThHTMLAttributes<HTMLTableCellElement>) => (
  <th {...p} className={`px-4 py-3 bg-secondary/60 text-muted-foreground font-medium ${p.className ?? ''}`} />
);
export const Td = (p: TdHTMLAttributes<HTMLTableCellElement>) => (
  <td {...p} className={`px-4 py-3 text-foreground ${p.className ?? ''}`} />
);
