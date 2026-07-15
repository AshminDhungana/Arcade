/** Format a duration in seconds as "1h 23m" / "45m" / "0m". */
export function formatDuration(totalSeconds: number): string {
  const s = Math.max(0, Math.round(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

/** Format a 0-23 hour as "3 PM" / "12 AM". */
export function formatHour(hour: number): string {
  const h12 = hour % 12 === 0 ? 12 : hour % 12;
  const suffix = hour < 12 ? 'AM' : 'PM';
  return `${h12} ${suffix}`;
}

/** Short weekday label for an ISO date "YYYY-MM-DD" (interpreted as UTC). */
export function formatWeekday(dateStr: string): string {
  const d = new Date(`${dateStr}T00:00:00Z`);
  return d.toLocaleDateString('en-US', { weekday: 'short', timeZone: 'UTC' });
}

/** Utilisation health colour (hex) for a 0-100 percentage. */
export function utilisationColor(pct: number): string {
  if (pct >= 85) return '#EF4444'; // red-500
  if (pct >= 60) return '#F59E0B'; // amber-500
  return '#22C55E'; // green-500
}
