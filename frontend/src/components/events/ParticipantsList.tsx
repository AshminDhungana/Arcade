import { Button } from '@/components/ui/Button';
import { Table, Th, Td } from '@/components/ui/Table';
import { Users } from 'lucide-react';
import type { EventSummaryResponse } from '@/types/events';

export function ParticipantsList({ summary, onRegister }: { summary: EventSummaryResponse; onRegister: () => void }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-medium text-foreground">Participants ({summary.participant_count})</h3>
        <Button variant="secondary" onClick={onRegister}><Users className="h-4 w-4" /> Register participant</Button>
      </div>
      {summary.participants.length === 0 ? (
        <p className="text-sm text-muted-foreground">No participants yet.</p>
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-border">
              <Th>Name</Th><Th>Seat</Th><Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {summary.participants.map((p) => (
              <tr key={p.id} className="border-b border-border">
                <Td>{p.name}</Td>
                <Td>{p.seat_id ?? '—'}</Td>
                <Td>
                  {p.eliminated
                    ? <span className="text-muted-foreground line-through">Eliminated</span>
                    : <span className="text-success">In contention</span>}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
