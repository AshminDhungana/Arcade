export function PageLoader() {
  return (
    <div className="flex h-64 items-center justify-center text-muted-foreground" role="status" aria-label="Loading page">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-primary" />
      <span className="ml-3">Loading…</span>
    </div>
  );
}
