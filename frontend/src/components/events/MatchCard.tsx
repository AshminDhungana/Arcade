import { Button } from '@/components/ui/Button';
import { CheckCircle } from 'lucide-react';
import type { ResolvedMatch } from './bracket';

function Slot({ name, isWinner, isLoser }: { name: string | null; isWinner: boolean; isLoser: boolean }) {
  if (!name) return <span className="text-sm text-muted-foreground">TBD</span>;
  return (
    <span className={`text-sm ${isWinner ? 'font-semibold text-success' : isLoser ? 'text-muted-foreground line-through' : 'text-foreground'}`}>
      {isWinner && <CheckCircle className="mr-1 inline h-4 w-4 align-middle text-success" aria-hidden="true" />}
      {name}
    </span>
  );
}

export function MatchCard({ rm, isAdmin, onRecord }: { rm: ResolvedMatch; isAdmin: boolean; onRecord: (rm: ResolvedMatch) => void }) {
  const { match, slotAName, slotBName, isBye, isReady, winnerName } = rm;
  const aWins = match.winner_id === match.slot_a_id;
  const bWins = match.winner_id === match.slot_b_id;

  return (
    <div className="w-full min-w-[200px] rounded-lg border border-border bg-card/60 p-3">
      <div className="flex flex-col gap-1.5">
        <Slot name={slotAName} isWinner={aWins} isLoser={bWins} />
        <div className="border-t border-border" />
        <Slot name={slotBName} isWinner={bWins} isLoser={aWins} />
      </div>
      <div className="mt-2">
        {isBye ? (
          <p className="text-xs text-muted-foreground">Bye — {slotAName ?? slotBName} advances</p>
        ) : match.status === 'COMPLETED' ? (
          <p className="text-xs text-success">Winner: {winnerName}</p>
        ) : isReady && isAdmin ? (
          <Button variant="secondary" className="w-full" onClick={() => onRecord(rm)}>Record result</Button>
        ) : (
          <p className="text-xs text-muted-foreground">Awaiting both players</p>
        )}
      </div>
    </div>
  );
}
