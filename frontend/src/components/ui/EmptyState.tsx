import type { ReactNode } from 'react';

export function EmptyState({ message, action }: { message: string; action?: ReactNode }) {
  return <div className="flex flex-col items-center gap-3 py-12 text-center text-slate-400">
    <p className="text-sm">{message}</p>
    {action}
  </div>;
}
