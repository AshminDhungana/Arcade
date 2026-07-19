import { useState } from 'react';
import { Plus, Shield, User, KeyRound } from 'lucide-react';
import {
  useStaff,
  useCreateStaff,
  useDeactivateStaff,
  useReactivateStaff,
  useChangeStaffPin,
} from '@/api/settings';
import { Button } from '@/components/ui/Button';
import { Table, Th, Td } from '@/components/ui/Table';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { toast } from '@/store/toastStore';
import type { Staff, StaffRole } from '@/types/settings';

const ROLE_BADGE_VARIANTS: Record<StaffRole, string> = {
  ADMIN: 'bg-purple-900/30 text-purple-300',
  CASHIER: 'bg-blue-900/30 text-blue-300',
};

interface StaffFormData {
  name: string;
  role: StaffRole;
  pin: string;
}

function StaffFormModal({
  open,
  onClose,
  title,
  onSubmit,
  isLoading,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  onSubmit: (data: StaffFormData) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState<StaffFormData>({
    name: '',
    role: 'CASHIER',
    pin: '',
  });
  const [errors, setErrors] = useState<Partial<Record<keyof StaffFormData, string>>>({});

  const handleChange = (field: keyof StaffFormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof StaffFormData, string>> = {};
    if (!formData.name.trim()) newErrors.name = 'Name is required';
    if (!formData.role) newErrors.role = 'Role is required';
    if (!formData.pin) {
      newErrors.pin = 'PIN is required';
    } else if (formData.pin.length < 4) {
      newErrors.pin = 'PIN must be at least 4 digits';
    } else if (!/^\d+$/.test(formData.pin)) {
      newErrors.pin = 'PIN must be numeric';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    onSubmit(formData);
  };

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          name="name"
          label="Name"
          value={formData.name}
          onChange={(e) => handleChange('name', e.target.value)}
          error={errors.name ?? null}
          placeholder="e.g. John Doe"
          autoFocus
        />

        <div>
          <label htmlFor="role" className="mb-1 block text-sm font-medium text-foreground">
            Role
          </label>
          <select
            id="role"
            value={formData.role}
            onChange={(e) => handleChange('role', e.target.value as StaffRole)}
            className="w-full rounded-lg border border-input bg-popover py-2.5 px-3 pr-8 text-sm text-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
            aria-invalid={!!errors.role}
          >
            <option value="ADMIN">Admin</option>
            <option value="CASHIER">Cashier</option>
          </select>
          {errors.role && (
            <p role="alert" className="mt-1 flex items-center gap-1 text-xs text-red-400">
              {errors.role}
            </p>
          )}
        </div>

        <Input
          name="pin"
          label="PIN (min 4 digits)"
          type="password"
          value={formData.pin}
          onChange={(e) => handleChange('pin', e.target.value)}
          error={errors.pin ?? null}
          placeholder="1234"
          minLength={4}
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="emerald" loading={isLoading}>
            Create
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ConfirmationModal({
  open,
  onClose,
  title,
  message,
  confirmLabel,
  onConfirm,
  isLoading,
  variant = 'danger',
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  isLoading: boolean;
  variant?: 'danger' | 'emerald';
}) {
  return (
    <Modal open={open} onClose={onClose} title={title}>
      <p className="mb-4 text-foreground">{message}</p>
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose} disabled={isLoading}>
          Cancel
        </Button>
        <Button variant={variant} onClick={onConfirm} loading={isLoading}>
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}

function PinChangeModal({
  open,
  staff,
  onClose,
  onConfirm,
  isLoading,
}: {
  open: boolean;
  staff: Staff | null;
  onClose: () => void;
  onConfirm: (pin: string) => void;
  isLoading: boolean;
}) {
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!pin) {
      setError('PIN is required');
    } else if (pin.length < 4) {
      setError('PIN must be at least 4 digits');
    } else if (pin.length > 20) {
      setError('PIN must be at most 20 digits');
    } else if (!/^\d+$/.test(pin)) {
      setError('PIN must be numeric');
    } else {
      setError(null);
      onConfirm(pin);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={`Change PIN — ${staff?.name ?? ''}`}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          name="newPin"
          label="New PIN (min 4 digits)"
          type="password"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          error={error ?? null}
          placeholder="1234"
          minLength={4}
          autoFocus
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="emerald" loading={isLoading}>
            Update PIN
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function roleBadge(role: StaffRole) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ROLE_BADGE_VARIANTS[role]}`}>
      {role}
    </span>
  );
}

function activeBadge(isActive: boolean) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        isActive
          ? 'bg-emerald-900/30 text-emerald-300'
          : 'bg-secondary text-muted-foreground'
      }`}
    >
      {isActive ? 'Active' : 'Inactive'}
    </span>
  );
}

export function StaffTab() {
  const [modalOpen, setModalOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<'deactivate' | 'reactivate' | null>(null);
  const [confirmStaffId, setConfirmStaffId] = useState<string | null>(null);
  const [confirmStaffName, setConfirmStaffName] = useState('');
  const [pinModalOpen, setPinModalOpen] = useState(false);
  const [pinStaff, setPinStaff] = useState<Staff | null>(null);

  const { data: staff = [], isLoading, isError, refetch } = useStaff();
  const createStaff = useCreateStaff();
  const deactivateStaff = useDeactivateStaff();
  const reactivateStaff = useReactivateStaff();
  const changePin = useChangeStaffPin();

  const handleSubmit = async (data: StaffFormData) => {
    try {
      await createStaff.mutateAsync(data);
      toast.success('Staff created successfully');
      setModalOpen(false);
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create staff';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    }
  };

  const handleDeactivate = async () => {
    if (!confirmStaffId) return;
    try {
      await deactivateStaff.mutateAsync(confirmStaffId);
      toast.success(`${confirmStaffName} deactivated`);
      setConfirmOpen(false);
      setConfirmAction(null);
      setConfirmStaffId(null);
      setConfirmStaffName('');
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to deactivate staff';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    }
  };

  const handleReactivate = async () => {
    if (!confirmStaffId) return;
    try {
      await reactivateStaff.mutateAsync(confirmStaffId);
      toast.success(`${confirmStaffName} reactivated`);
      setConfirmOpen(false);
      setConfirmAction(null);
      setConfirmStaffId(null);
      setConfirmStaffName('');
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to reactivate staff';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    }
  };

  const openConfirm = (action: 'deactivate' | 'reactivate', staff: Staff) => {
    setConfirmAction(action);
    setConfirmStaffId(staff.id);
    setConfirmStaffName(staff.name);
    setConfirmOpen(true);
  };

  const openPinModal = (staff: Staff) => {
    setPinStaff(staff);
    setPinModalOpen(true);
  };

  const handleChangePin = async (pin: string) => {
    if (!pinStaff) return;
    try {
      await changePin.mutateAsync({ id: pinStaff.id, pin });
      toast.success(`PIN updated for ${pinStaff.name}`);
      setPinModalOpen(false);
      setPinStaff(null);
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to change PIN';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold text-foreground">Staff</h1>
        </div>
        <div className="flex h-64 items-center justify-center text-muted-foreground">Loading…</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-foreground">Staff</h1>
        <Button variant="emerald" onClick={() => setModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Staff
        </Button>
      </div>

      {isError && <ErrorState message="Failed to load staff. Admin required." onRetry={refetch} />}

      <section className="rounded-xl border border-border bg-card p-5">
        {staff.length === 0 ? (
          <EmptyState message="No staff yet. Add one to get started." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-border">
                <Th className="text-left">Name</Th>
                <Th className="text-left">Role</Th>
                <Th className="text-left">Status</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {staff.map((s) => (
                <tr key={s.id} className="border-b border-border hover:bg-secondary">
                  <Td className="font-medium">{s.name}</Td>
                  <Td>{roleBadge(s.role)}</Td>
                  <Td>{activeBadge(s.is_active)}</Td>
                  <Td className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      {s.is_active ? (
                        <>
                          <Button
                            variant="secondary"
                            aria-label={`Change PIN for ${s.name}`}
                            onClick={() => openPinModal(s)}
                            disabled={changePin.isPending}
                          >
                            <KeyRound className="h-4 w-4 mr-1" />
                            Change PIN
                          </Button>
                          <Button
                            variant="secondary"
                            aria-label={`Deactivate ${s.name}`}
                            onClick={() => openConfirm('deactivate', s)}
                            disabled={deactivateStaff.isPending}
                          >
                            <User className="h-4 w-4 mr-1" />
                            Deactivate
                          </Button>
                        </>
                      ) : (
                        <Button
                          variant="emerald"
                          aria-label={`Reactivate ${s.name}`}
                          onClick={() => openConfirm('reactivate', s)}
                          disabled={reactivateStaff.isPending}
                        >
                          <Shield className="h-4 w-4 mr-1" />
                          Reactivate
                        </Button>
                      )}
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </section>

      {/* Create Staff Modal */}
      <StaffFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Add Staff"
        onSubmit={handleSubmit}
        isLoading={createStaff.isPending}
      />

      {/* Deactivate/Reactivate Confirmation Modal */}
      {confirmOpen && confirmAction && confirmStaffId && confirmStaffName && (
        <ConfirmationModal
          open={confirmOpen}
          onClose={() => {
            setConfirmOpen(false);
            setConfirmAction(null);
            setConfirmStaffId(null);
            setConfirmStaffName('');
          }}
          title={confirmAction === 'deactivate' ? 'Deactivate Staff' : 'Reactivate Staff'}
          message={
            confirmAction === 'deactivate'
              ? `Are you sure you want to deactivate "${confirmStaffName}"? They will no longer be able to log in.`
              : `Are you sure you want to reactivate "${confirmStaffName}"? They will be able to log in again.`
          }
          confirmLabel={confirmAction === 'deactivate' ? 'Deactivate' : 'Reactivate'}
          onConfirm={confirmAction === 'deactivate' ? handleDeactivate : handleReactivate}
          isLoading={confirmAction === 'deactivate' ? deactivateStaff.isPending : reactivateStaff.isPending}
          variant={confirmAction === 'deactivate' ? 'danger' : 'emerald'}
        />
      )}

      {/* Change PIN Modal */}
      {pinModalOpen && pinStaff && (
        <PinChangeModal
          open={pinModalOpen}
          staff={pinStaff}
          onClose={() => {
            setPinModalOpen(false);
            setPinStaff(null);
          }}
          onConfirm={handleChangePin}
          isLoading={changePin.isPending}
        />
      )}
    </div>
  );
}

export default StaffTab;
