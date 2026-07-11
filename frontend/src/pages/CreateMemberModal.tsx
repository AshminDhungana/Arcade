import { useState, type FormEvent } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

interface CreateMemberModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (name: string, phone: string) => Promise<void>;
  onSuccess: () => void;
  isLoading: boolean;
}

export function CreateMemberModal({ open, onClose, onSubmit, onSuccess, isLoading }: CreateMemberModalProps) {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [nameError, setNameError] = useState<string | null>(null);
  const [phoneError, setPhoneError] = useState<string | null>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setNameError(null);
    setPhoneError(null);

    const trimmedName = name.trim();
    const trimmedPhone = phone.trim();

    let valid = true;
    if (!trimmedName) {
      setNameError('Name is required');
      valid = false;
    }
    if (!trimmedPhone) {
      setPhoneError('Phone is required');
      valid = false;
    }

    if (!valid) return;

    onSubmit(trimmedName, trimmedPhone).then(() => {
      setName('');
      setPhone('');
      onSuccess();
    });
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New Member"
      children={
        <form id="create-member-form" onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            error={nameError}
            placeholder="John Doe"
            autoFocus
          />
          <Input
            label="Phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            error={phoneError}
            placeholder="9800000000"
          />
        </form>
      }
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" type="button" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" form="create-member-form" loading={isLoading}>
            Create Member
          </Button>
        </div>
      }
    />
  );
}
