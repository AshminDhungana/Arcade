import { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { toast } from '@/store/toastStore';
import { useRegisterParticipant } from '@/api/events';
import { useActiveMembers } from '@/api/members';
import { useAvailableSeats } from '@/api/seats';
import { formatPaise } from '@/hooks/useFormatPaise';

export function RegisterParticipantModal({
  open,
  eventId,
  onClose,
  entryFeePaise = 0,
}: {
  open: boolean;
  eventId: string;
  onClose: () => void;
  entryFeePaise?: number;
}) {
  const register = useRegisterParticipant(eventId);
  const { data: members, isLoading: membersLoading } = useActiveMembers();
  const { data: seats, isLoading: seatsLoading } = useAvailableSeats();
  const [mode, setMode] = useState<'member' | 'walkin'>('member');
  const [memberId, setMemberId] = useState('');
  const [walkinName, setWalkinName] = useState('');
  const [seatId, setSeatId] = useState('');

  const selectedMember = members?.find((m) => m.id === memberId);
  const walletPreview = selectedMember
    ? selectedMember.wallet_balance_paise - entryFeePaise
    : null;

  // Reset form when modal opens/closes
  useEffect(() => {
    if (open) {
      setMode('member');
      setMemberId('');
      setWalkinName('');
      setSeatId('');
    }
  }, [open]);

  async function handleSubmit() {
    try {
      if (mode === 'member') {
        if (!memberId) {
          toast.error('Please select a member');
          return;
        }
        await register.mutateAsync({ member_id: memberId, seat_id: seatId || undefined });
      } else {
        if (!walkinName.trim()) {
          toast.error('Please enter a name');
          return;
        }
        await register.mutateAsync({ name: walkinName.trim(), seat_id: seatId || undefined });
      }
      toast.success('Participant registered');
      onClose();
    } catch {
      toast.error('Failed to register participant');
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Register participant"
      footer={
        <Button onClick={handleSubmit} loading={register.isPending}>
          Register
        </Button>
      }
    >
      <div className="space-y-4">
        <fieldset className="flex gap-4">
          <legend className="text-sm font-medium text-foreground mb-2">Registration type</legend>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              value="member"
              checked={mode === 'member'}
              onChange={() => setMode('member')}
              className="h-4 w-4 text-primary focus:ring-primary"
            />
            <span>Member</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              value="walkin"
              checked={mode === 'walkin'}
              onChange={() => setMode('walkin')}
              className="h-4 w-4 text-primary focus:ring-primary"
            />
            <span>Walk-in</span>
          </label>
        </fieldset>

        {mode === 'member' && (
          <div className="space-y-3">
            <div>
              <label id="member-label" className="block text-sm font-medium text-foreground mb-1.5">Member</label>
              <select
                id="member-select"
                data-testid="member-select"
                aria-labelledby="member-label"
                value={memberId}
                onChange={(e) => setMemberId(e.target.value)}
                className="w-full rounded-md border border-input bg-popover px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                required
                disabled={membersLoading}
              >
                <option value="">Select member</option>
                {members?.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.phone})
                  </option>
                ))}
              </select>
            </div>
            {entryFeePaise > 0 && selectedMember && (
              <div className="text-sm text-muted-foreground space-y-1">
                <p>Wallet balance: <strong>{formatPaise(selectedMember.wallet_balance_paise)}</strong></p>
                <p>Entry fee: <strong>{formatPaise(entryFeePaise)}</strong></p>
                <p className={walletPreview !== null && walletPreview < 0 ? 'text-destructive' : ''}>
                  After registration: <strong>{formatPaise(Math.max(0, walletPreview))}</strong>
                </p>
              </div>
            )}
          </div>
        )}

        {mode === 'walkin' && (
          <Input
            id="walkin-name"
            label="Participant name"
            value={walkinName}
            onChange={(e) => setWalkinName(e.target.value)}
            autoFocus
            required
            placeholder="Enter name"
          />
        )}

        {!seatsLoading && (seats?.length ?? 0) > 0 && (
          <div>
            <label id="seat-label" className="block text-sm font-medium text-foreground mb-1.5">Seat (optional)</label>
            <select
              id="seat-select"
              data-testid="seat-select"
              aria-labelledby="seat-label"
              value={seatId}
              onChange={(e) => setSeatId(e.target.value)}
              className="w-full rounded-md border border-input bg-popover px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="">Assign seat</option>
              {seats.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.status})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    </Modal>
  );
}
