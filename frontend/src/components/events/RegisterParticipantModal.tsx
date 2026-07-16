import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { toast } from '@/store/toastStore';
import { useRegisterParticipant } from '@/api/events';

export function RegisterParticipantModal({ open, eventId, onClose }: { open: boolean; eventId: string; onClose: () => void }) {
  const register = useRegisterParticipant(eventId);
  const [name, setName] = useState('');

  async function handleSubmit() {
    try {
      await register.mutateAsync({ name });
      toast.success('Participant registered');
      onClose();
      setName('');
    } catch {
      toast.error('Failed to register participant');
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Register participant"
      footer={<Button onClick={handleSubmit} loading={register.isPending}>Register</Button>}>
      <Input label="Participant name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
    </Modal>
  );
}
