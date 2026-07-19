import { AlertTriangle, WifiOff, Thermometer } from 'lucide-react';

export type AlertKind = 'overheating' | 'stale' | 'offline';

export interface UnifiedAlert {
  seat_id: string;
  seat_name: string;
  kind: AlertKind;
  reasons: string[];
}

const META: Record<AlertKind, { border: string; text: string; icon: typeof AlertTriangle; title: string }> = {
  overheating: { border: 'border-l-destructive', text: 'text-destructive', icon: Thermometer, title: 'Overheating' },
  stale: { border: 'border-l-warning', text: 'text-warning', icon: AlertTriangle, title: 'No health report' },
  offline: { border: 'border-l-muted-foreground', text: 'text-muted-foreground', icon: WifiOff, title: 'Offline' },
};

export function HealthAlertCard({ alert }: { alert: UnifiedAlert }) {
  const m = META[alert.kind];
  const Icon = m.icon;
  return (
    <div
      className={`flex items-start gap-3 rounded-lg border border-border border-l-4 ${m.border} bg-card p-3`}
      role="alert"
    >
      <Icon className={`h-5 w-5 ${m.text}`} aria-hidden="true" />
      <div>
        <p className={`font-medium ${m.text}`}>
          {m.title}: {alert.seat_name}
        </p>
        {alert.reasons.length > 0 && (
          <p className="text-sm text-muted-foreground">{alert.reasons.join(', ')}</p>
        )}
      </div>
    </div>
  );
}
