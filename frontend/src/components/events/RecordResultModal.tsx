import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { toast } from '@/store/toastStore';
import { useRecordMatchResult } from '@/api/events';
import type { ResolvedMatch } from './bracket';

export function RecordResultModal({ eventId, rm, onClose }: { eventId: string; rm: ResolvedMatch; onClose: () => void }) {
  const record = useRecordMatchResult(eventId);

  async function pick(winnerId: string) {
    try {
      await record.mutateAsync({ match_id: rm.match.id, winner_id: winnerId });
      toast.success('Result recorded');
      onClose();
    } catch {
      toast.error('Failed to record result');
    }
  }

  return (
    <Modal open onClose={onClose} title="Record result"
      footer={<Button variant="secondary" onClick={onClose}>Cancel</Button>}>
      <div className="space-y-2">
        <p className="text-sm text-muted-foreground">Select the winner of this match.</p>
        <Button className="w-full" disabled={!rm.slotAName} onClick={() => rm.slotAId && pick(rm.slotAId)}>
          {rm.slotAName ?? 'Player A'}
        </Button>
        <Button className="w-full" disabled={!rm.slotBName} onClick={() => rm.slotBId && pick(rm.slotBId)}>
          {rm.slotBName ?? 'Player B'}
        </Button>
      </div>
    </Modal>
  );
}
