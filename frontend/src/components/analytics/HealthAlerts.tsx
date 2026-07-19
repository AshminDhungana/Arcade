import { SeatStatus } from '@/types/seat';
import type { Seat } from '@/types/seat';
import type { HealthAlert } from '@/types/analytics';
import { HealthAlertCard, type UnifiedAlert } from './HealthAlertCard';

function describeReasons(reasons: string[]): string[] {
  return reasons.map((r) =>
    r === 'cpu_temp_red'
      ? 'CPU temperature in red zone'
      : r === 'no_health_report'
        ? 'No health report in 5 min'
        : r,
  );
}

export function HealthAlerts({ alerts, seats }: { alerts: HealthAlert[]; seats: Seat[] }) {
  const fromSummary: UnifiedAlert[] = alerts.map((a) => ({
    seat_id: a.seat_id,
    seat_name: a.seat_name,
    kind: a.reasons.includes('cpu_temp_red') ? 'overheating' : 'stale',
    reasons: describeReasons(a.reasons),
  }));

  const offline: UnifiedAlert[] = seats
    .filter((s) => s.status === SeatStatus.OFFLINE || s.status === SeatStatus.UNREACHABLE)
    .map((s) => ({
      seat_id: s.id,
      seat_name: s.name,
      kind: 'offline' as const,
      reasons: ['Seat is offline'],
    }));

  const all = [...fromSummary, ...offline];

  return (
    <section className="rounded-xl border border-border bg-card p-4" aria-label="Health alerts">
      <h2 className="mb-3 text-base font-medium text-foreground">Health alerts</h2>
      {all.length === 0 ? (
        <p className="text-sm text-muted-foreground">All seats healthy.</p>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {all.map((a) => (
            <HealthAlertCard key={`${a.kind}-${a.seat_id}`} alert={a} />
          ))}
        </div>
      )}
    </section>
  );
}
