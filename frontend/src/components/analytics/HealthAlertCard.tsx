import { AlertTriangle, WifiOff, Thermometer } from 'lucide-react';

export type AlertKind = 'overheating' | 'stale' | 'offline';

export interface UnifiedAlert {
  seat_id: string;
  seat_name: string;
  kind: AlertKind;
  reasons: string[];
}

const META: Record<AlertKind, { border: string; text: string; icon: typeof AlertTriangle; title: string }> = {
  overheating: { border: 'border-l-red-500', text: 'text-red-300', icon: Thermometer, title: 'Overheating' },
  stale: { border: 'border-l-amber-500', text: 'text-amber-300', icon: AlertTriangle, title: 'No health report' },
  offline: { border: 'border-l-slate-500', text: 'text-slate-300', icon: WifiOff, title: 'Offline' },
};

export function HealthAlertCard({ alert }: { alert: UnifiedAlert }) {
  const m = META[alert.kind];
  const Icon = m.icon;
  return (
    <div
      className={`flex items-start gap-3 rounded-lg border border-slate-700 border-l-4 ${m.border} bg-slate-800 p-3`}
      role="alert"
    >
      <Icon className={`h-5 w-5 ${m.text}`} aria-hidden="true" />
      <div>
        <p className={`font-medium ${m.text}`}>
          {m.title}: {alert.seat_name}
        </p>
        {alert.reasons.length > 0 && (
          <p className="text-sm text-slate-400">{alert.reasons.join(', ')}</p>
        )}
      </div>
    </div>
  );
}
