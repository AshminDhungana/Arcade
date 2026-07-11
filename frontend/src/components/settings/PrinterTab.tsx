import { EmptyState } from '@/components/ui/EmptyState';

export function PrinterTab() {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800 p-5">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Printer</h2>
      <EmptyState message="Printer panel — coming soon in Task 32" />
    </section>
  );
}
