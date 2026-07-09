// frontend/src/utils/formatDuration.ts
/**
 * Format seconds into human-readable duration.
 * Examples: "30s", "5m 30s", "2h 15m", "1h 30m 5s"
 */
export function formatDuration(seconds: number): string {
  if (seconds < 0) return '0s';

  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const parts: string[] = [];
  if (hrs > 0) parts.push(`${hrs}h`);
  if (mins > 0) parts.push(`${mins}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

  return parts.join(' ');
}
