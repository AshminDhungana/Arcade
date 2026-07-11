import { EmptyState } from '@/components/ui/EmptyState';

export function MenuTab() {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800 p-5">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Menu</h2>
      <EmptyState message="Menu panel — coming soon in Task 31" />
    </section>
  );
}
