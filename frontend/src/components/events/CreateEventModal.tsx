import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { toast } from '@/store/toastStore';
import { useCreateEvent } from '@/api/events';
import type { EventBracketType } from '@/types/events';

export function CreateEventModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const create = useCreateEvent();
  const [name, setName] = useState('');
  const [game, setGame] = useState('');
  const [date, setDate] = useState('');
  const [entryFee, setEntryFee] = useState('');
  const [prizePool, setPrizePool] = useState('');
  const [bracket, setBracket] = useState<EventBracketType>('SINGLE_ELIMINATION');

  async function handleSubmit() {
    try {
      await create.mutateAsync({
        name,
        game_title: game,
        event_date: new Date(date || Date.now()).toISOString(),
        entry_fee_paise: Math.round(Number(entryFee || 0) * 100),
        prize_pool_paise: Math.round(Number(prizePool || 0) * 100),
        bracket_type: bracket,
      });
      toast.success('Event created');
      onClose();
      setName(''); setGame(''); setDate(''); setEntryFee(''); setPrizePool(''); setBracket('SINGLE_ELIMINATION');
    } catch {
      toast.error('Failed to create event');
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New Event"
      footer={<Button onClick={handleSubmit} loading={create.isPending}>Create</Button>}>
      <div className="space-y-3">
        <Input name="name" label="Name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        <Input name="game_title" label="Game" value={game} onChange={(e) => setGame(e.target.value)} />
        <Input name="event_date" label="Date & time" type="datetime-local" value={date} onChange={(e) => setDate(e.target.value)} />
        <Input name="entry_fee" label="Entry fee (₹)" type="number" min={0} value={entryFee} onChange={(e) => setEntryFee(e.target.value)} />
        <Input name="prize_pool" label="Prize pool (₹)" type="number" min={0} value={prizePool} onChange={(e) => setPrizePool(e.target.value)} />
        <label className="block text-sm font-medium text-foreground">
          Bracket type
          <select
            value={bracket}
            onChange={(e) => setBracket(e.target.value as EventBracketType)}
            className="mt-1 w-full rounded-lg border border-input bg-popover px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="SINGLE_ELIMINATION">Single elimination</option>
            <option value="DOUBLE_ELIMINATION">Double elimination</option>
          </select>
        </label>
      </div>
    </Modal>
  );
}
