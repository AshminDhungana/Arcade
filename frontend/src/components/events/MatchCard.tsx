import { Button } from '@/components/ui/Button';
import { CheckCircle } from 'lucide-react';
import type { ResolvedMatch } from './bracket';

function Slot({ name, isWinner, isLoser }: { name: string | null; isWinner: boolean; isLoser: boolean }) {
  if (!name) return <span className="text-sm text-slate-500">TBD</span>;
  return (
    <span className={`text-sm ${isWinner ? 'font-semibold text-emerald-400' : isLoser ? 'text-slate-500 line-through' : 'text-slate-200'}`}>
      {isWinner && <CheckCircle className="mr-1 inline h-4 w-4 align-middle text-emerald-400" aria-hidden="true" />}
      {name}
    </span>
  );
}

export function MatchCard({ rm, isAdmin, onRecord }: { rm: ResolvedMatch; isAdmin: boolean; onRecord: (rm: ResolvedMatch) => void }) {
  const { match, slotAName, slotBName, isBye, isReady, winnerName } = rm;
  const aWins = match.winner_id === match.slot_a_id;
  const bWins = match.winner_id === match.slot_b_id;

  return (
    <div className="w-full min-w-[200px] rounded-lg border border-slate-700 bg-slate-800/60 p-3">
      <div className="flex flex-col gap-1.5">
        <Slot name={slotAName} isWinner={aWins} isLoser={bWins} />
        <div className="border-t border-slate-700/50" />
        <Slot name={slotBName} isWinner={bWins} isLoser={aWins} />
      </div>
      <div className="mt-2">
        {isBye ? (
          <p className="text-xs text-slate-500">Bye — {slotAName ?? slotBName} advances</p>
        ) : match.status === 'COMPLETED' ? (
          <p className="text-xs text-emerald-400">Winner: {winnerName}</p>
        ) : isReady && isAdmin ? (
          <Button variant="secondary" className="w-full" onClick={() => onRecord(rm)}>Record result</Button>
        ) : (
          <p className="text-xs text-slate-500">Awaiting both players</p>
        )}
      </div>
    </div>
  );
}
