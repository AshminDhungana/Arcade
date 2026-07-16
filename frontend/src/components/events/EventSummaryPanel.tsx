import { Trophy } from 'lucide-react';
import { formatPaise } from '@/hooks/useFormatPaise';
import type { EventSummaryResponse } from '@/types/events';

export function EventSummaryPanel({ summary }: { summary: EventSummaryResponse }) {
  const champion = summary.champion_participant_id
    ? summary.participants.find((p) => p.id === summary.champion_participant_id)
    : undefined;
  const kpis = [
    { label: 'Prize pool', value: formatPaise(summary.prize_pool_paise) },
    { label: 'Entry-fee revenue', value: formatPaise(summary.entry_fee_revenue_paise) },
    { label: 'Participants', value: String(summary.participant_count) },
    { label: 'Matches completed', value: `${summary.completed_match_count}/${summary.match_count}` },
  ];
  return (
    <div className="space-y-4">
      {champion && (
        <div className="flex items-center gap-3 rounded-xl border border-amber-500/40 bg-amber-900/20 p-4">
          <Trophy className="h-6 w-6 text-amber-400" aria-hidden="true" />
          <div>
            <p className="text-sm text-amber-300">Champion</p>
            <p className="text-xl font-semibold text-white">{champion.name}</p>
          </div>
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((k) => (
          <div key={k.label} className="flex min-h-[96px] flex-col justify-between rounded-xl border border-slate-700 bg-slate-800 p-4 shadow-sm">
            <span className="text-sm text-slate-400">{k.label}</span>
            <p className="mt-2 text-2xl font-semibold tabular-nums text-white">{k.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
