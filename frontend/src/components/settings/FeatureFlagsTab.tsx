import { EmptyState } from '@/components/ui/EmptyState';

export function FeatureFlagsTab() {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-800 p-5">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Feature Flags</h2>
      <EmptyState message="Feature Flags panel — coming soon in Task 27" />
    </section>
  );
}
