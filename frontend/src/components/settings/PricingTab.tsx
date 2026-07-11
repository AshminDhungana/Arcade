import { EmptyState } from '@/components/ui/EmptyState';

export function PricingTab() {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800 p-5">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Pricing</h2>
      <EmptyState message="Pricing panel — coming soon in Task 28" />
    </section>
  );
}
