import { useAuthStore } from '@/store/authStore';
import { Trophy } from 'lucide-react';
import { buildBracket, type ResolvedMatch } from './bracket';
import { MatchCard } from './MatchCard';
import type { EventSummaryResponse } from '@/types/events';
import { RecordResultModal } from './RecordResultModal';
import { useState } from 'react';

export function BracketView({ summary, eventId }: { summary: EventSummaryResponse; eventId: string }) {
  const role = useAuthStore((s) => s.staff?.role);
  const isAdmin = role === 'ADMIN';
  const view = buildBracket(summary.matches, summary.participants);
  const [recording, setRecording] = useState<ResolvedMatch | null>(null);

  if (summary.matches.length === 0) {
    return <p className="text-sm text-muted-foreground">Bracket not generated yet — register at least 2 participants.</p>;
  }

  return (
    <div className="space-y-6">
      {view.championName && (
        <div className="flex items-center gap-3 rounded-xl border border-amber-500/40 bg-amber-900/20 p-4">
          <Trophy className="h-6 w-6 text-amber-400" aria-hidden="true" />
          <div>
            <p className="text-sm text-amber-300">Champion</p>
            <p className="text-xl font-semibold text-white">{view.championName}</p>
          </div>
        </div>
      )}
      {view.groups.map((g) => (
        <section key={g.group} aria-label={g.title}>
          <h3 className="mb-2 text-base font-medium text-foreground">{g.title}</h3>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {g.columns.map((col) => (
              <div key={col.round} className="flex shrink-0 flex-col gap-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Round {col.round}</p>
                {col.matches.map((rm) => (
                  <MatchCard key={rm.match.id} rm={rm} isAdmin={isAdmin} onRecord={setRecording} />
                ))}
              </div>
            ))}
          </div>
        </section>
      ))}
      {recording && (
        <RecordResultModal
          eventId={eventId}
          rm={recording}
          onClose={() => setRecording(null)}
        />
      )}
    </div>
  );
}
