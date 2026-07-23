import { useState, useMemo, useEffect, useCallback } from 'react';
import { Plus, Monitor, Settings, Trash2 } from 'lucide-react';
import {
  useSeats,
  useCreateSeat,
  useUpdateSeat,
  useDeleteSeat,
  useZones,
} from '@/api/settings';
import { Button } from '@/components/ui/Button';
import { Table, Th, Td } from '@/components/ui/Table';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { toast } from '@/store/toastStore';
import type { Seat, SeatStatus, SeatFormData } from '@/types/settings';

const STATUS_BADGE_VARIANTS: Record<SeatStatus, string> = {
  AVAILABLE: 'bg-emerald-900/30 text-emerald-300',
  IN_USE: 'bg-blue-900/30 text-blue-300',
  RESERVED: 'bg-amber-900/30 text-amber-300',
  PAUSED: 'bg-orange-900/30 text-orange-300',
  MAINTENANCE: 'bg-violet-900/30 text-violet-300',
  OFFLINE: 'bg-slate-900/30 text-slate-300',
  BOOTING: 'bg-cyan-900/30 text-cyan-300',
  UNREACHABLE: 'bg-red-900/30 text-red-300',
  EXPIRED: 'bg-rose-900/30 text-rose-300',
};

function SeatFormModal({
  open,
  onClose,
  title,
  onSubmit,
  isLoading,
  initialData,
  zones,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  onSubmit: (data: SeatFormData) => void;
  isLoading: boolean;
  initialData?: SeatFormData | null;
  zones: Array<{ id: string; name: string }>;
}) {
  const [formData, setFormData] = useState<SeatFormData>({
    name: '',
    zone_id: '',
    mac_address: '',
    plug_id: '',
    is_console: false,
    notes: '',
  });
  const [errors, setErrors] = useState<Partial<Record<keyof SeatFormData, string>>>({});

  const resetForm = useCallback(() => {
    if (initialData) {
      setFormData({
        name: initialData.name,
        zone_id: initialData.zone_id,
        mac_address: initialData.mac_address,
        plug_id: initialData.plug_id,
        is_console: initialData.is_console,
        notes: initialData.notes,
      });
    } else {
      setFormData({
        name: '',
        zone_id: '',
        mac_address: '',
        plug_id: '',
        is_console: false,
        notes: '',
      });
    }
    setErrors({});
  }, [initialData]);

  // Reset form when modal opens/closes or initialData changes
  useEffect(() => {
    resetForm();
  }, [open, resetForm]);

  const handleChange = (field: keyof SeatFormData, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof SeatFormData, string>> = {};
    if (!formData.name.trim()) newErrors.name = 'Name is required';
    if (!formData.zone_id) newErrors.zone_id = 'Zone is required';
    if (formData.mac_address && !/^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/.test(formData.mac_address)) {
      newErrors.mac_address = 'Invalid MAC address format (aa:bb:cc:dd:ee:ff)';
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
          placeholder="e.g. PC-01"
          autoFocus
        />

        <div>
          <label htmlFor="zone_id" className="mb-1 block text-sm font-medium text-foreground">
            Zone
          </label>
          <select
            id="zone_id"
            value={formData.zone_id}
            onChange={(e) => handleChange('zone_id', e.target.value)}
            className="w-full rounded-lg border border-input bg-popover py-2.5 px-3 pr-8 text-sm text-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
            aria-invalid={!!errors.zone_id}
          >
            <option value="">Select zone</option>
            {zones.map((zone) => (
              <option key={zone.id} value={zone.id}>
                {zone.name}
              </option>
            ))}
          </select>
          {errors.zone_id && (
            <p role="alert" className="mt-1 flex items-center gap-1 text-xs text-red-400">
              {errors.zone_id}
            </p>
          )}
        </div>

        <Input
          name="mac_address"
          label="MAC Address (optional)"
          value={formData.mac_address}
          onChange={(e) => handleChange('mac_address', e.target.value.toLowerCase())}
          error={errors.mac_address ?? null}
          placeholder="aa:bb:cc:dd:ee:ff"
        />

        <Input
          name="plug_id"
          label="Plug ID (optional)"
          value={formData.plug_id}
          onChange={(e) => handleChange('plug_id', e.target.value)}
          placeholder="Tuya plug device ID"
        />

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="is_console"
            checked={formData.is_console}
            onChange={(e) => handleChange('is_console', e.target.checked)}
            className="h-4 w-4 rounded border-input bg-background focus:ring-ring focus:ring-2"
          />
          <label htmlFor="is_console" className="text-sm font-medium text-foreground">
            Is Console (Smart Plug Controlled)
          </label>
        </div>

        <Textarea
          name="notes"
          label="Notes (optional)"
          value={formData.notes}
          onChange={(e) => handleChange('notes', e.target.value)}
          placeholder="Additional notes"
          rows={2}
        />

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="emerald" loading={isLoading}>
            {initialData ? 'Update' : 'Create'}
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
  if (!open) return null;
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

function statusBadge(status: SeatStatus) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE_VARIANTS[status]}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

function consoleBadge(isConsole: boolean) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
      isConsole
        ? 'bg-purple-900/30 text-purple-300'
        : 'bg-slate-900/30 text-slate-300'
    }`}>
      {isConsole ? 'Console' : 'PC'}
    </span>
  );
}

export function SeatsTab() {
  const [modalOpen, setModalOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmSeatId, setConfirmSeatId] = useState<string | null>(null);
  const [confirmSeatName, setConfirmSeatName] = useState('');
  const [editingSeat, setEditingSeat] = useState<Seat | null>(null);
  const [selectedZoneId, setSelectedZoneId] = useState<string>('all');

  const { data: seats = [], isLoading, isError, refetch } = useSeats();
  const createSeat = useCreateSeat();
  const updateSeat = useUpdateSeat();
  const deleteSeat = useDeleteSeat();
  const { data: zones = [], isLoading: zonesLoading } = useZones();

  const filteredSeats = useMemo(() => {
    if (selectedZoneId === 'all') return seats;
    return seats.filter((s) => s.zone_id === selectedZoneId);
  }, [seats, selectedZoneId]);

  const handleSubmit = async (data: SeatFormData) => {
    try {
      if (editingSeat) {
        const { name, zone_id, mac_address, plug_id, is_console, notes } = data;
        await updateSeat.mutateAsync({
          id: editingSeat.id,
          data: { name, zone_id, mac_address: mac_address || null, plug_id: plug_id || null, is_console, notes: notes || null },
        });
        toast.success('Seat updated successfully');
      } else {
        const { name, zone_id, mac_address, plug_id, is_console, notes } = data;
        await createSeat.mutateAsync({
          name,
          zone_id,
          mac_address: mac_address || null,
          plug_id: plug_id || null,
          is_console,
          notes: notes || null,
        });
        toast.success('Seat created successfully');
      }
      setModalOpen(false);
      setEditingSeat(null);
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Operation failed';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else if (msg.includes('404')) {
        toast.error('Zone not found');
      } else {
        toast.error(msg);
      }
    }
  };

  const handleDelete = async () => {
    if (!confirmSeatId) return;
    try {
      await deleteSeat.mutateAsync(confirmSeatId);
      toast.success(`${confirmSeatName} deleted`);
      setConfirmOpen(false);
      setConfirmSeatId(null);
      setConfirmSeatName('');
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete seat';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    }
  };

  const openDeleteConfirm = (seat: Seat) => {
    setConfirmSeatId(seat.id);
    setConfirmSeatName(seat.name);
    setConfirmOpen(true);
  };

  const openEditModal = (seat: Seat) => {
    setEditingSeat(seat);
    setModalOpen(true);
  };

  const openCreateModal = () => {
    setEditingSeat(null);
    setModalOpen(true);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold text-foreground">Seats</h1>
        </div>
        <div className="flex h-64 items-center justify-center text-muted-foreground">Loading…</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-foreground">Seats</h1>
        <Button variant="emerald" onClick={openCreateModal} disabled={zonesLoading || zones.length === 0}>
          <Plus className="h-4 w-4 mr-2" />
          Add Seat
        </Button>
      </div>

      {isError && <p className="text-red-400">Failed to load seats. Admin required.</p>}

      {/* Zone Filter */}
      <div className="flex items-center gap-4">
        <label htmlFor="zone-filter" className="text-sm font-medium text-foreground">
          Filter by Zone:
        </label>
        <select
          id="zone-filter"
          value={selectedZoneId}
          onChange={(e) => setSelectedZoneId(e.target.value)}
          disabled={zonesLoading}
          className="w-full rounded-lg border border-input bg-popover py-2.5 px-3 pr-8 text-sm text-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
        >
          <option value="all">All Zones</option>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name}
            </option>
          ))}
        </select>
        {zonesLoading && <span className="text-xs text-muted-foreground">Loading zones…</span>}
      </div>

      <section className="rounded-xl border border-border bg-card p-5">
        {filteredSeats.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
            <Monitor className="h-12 w-12 mb-4 text-muted-foreground/50" />
            <p className="text-lg">No seats found</p>
            <p className="text-sm">
              {selectedZoneId !== 'all'
                ? 'No seats in this zone. Create one or select another zone.'
                : 'Create your first seat to get started.'}
            </p>
          </div>
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-border">
                <Th className="text-left">Name</Th>
                <Th className="text-left">Zone</Th>
                <Th className="text-left">Type</Th>
                <Th className="text-left">Status</Th>
                <Th className="text-left">MAC Address</Th>
                <Th className="text-left">Plug ID</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {filteredSeats.map((seat) => (
                <tr key={seat.id} className="border-b border-border hover:bg-secondary">
                  <Td className="font-medium">{seat.name}</Td>
                  <Td>{seat.zone_name ?? '—'}</Td>
                  <Td>{consoleBadge(seat.is_console)}</Td>
                  <Td>{statusBadge(seat.status as SeatStatus)}</Td>
                  <Td className="font-mono text-sm">{seat.mac_address ?? '—'}</Td>
                  <Td className="font-mono text-sm">{seat.plug_id ?? '—'}</Td>
                  <Td className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="secondary"
                        size="sm"
                        aria-label={`Edit ${seat.name}`}
                        onClick={() => openEditModal(seat)}
                        disabled={updateSeat.isPending}
                      >
                        <Settings className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        aria-label={`Delete ${seat.name}`}
                        onClick={() => openDeleteConfirm(seat)}
                        disabled={deleteSeat.isPending}
                      >
                        <Trash2 className="h-4 w-4 text-red-400" />
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </section>

      {/* Create/Edit Seat Modal */}
      <SeatFormModal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditingSeat(null);
        }}
        title={editingSeat ? `Edit Seat — ${editingSeat.name}` : 'Add Seat'}
        onSubmit={handleSubmit}
        isLoading={createSeat.isPending || updateSeat.isPending}
        initialData={editingSeat
          ? {
              name: editingSeat.name,
              zone_id: editingSeat.zone_id,
              mac_address: editingSeat.mac_address ?? '',
              plug_id: editingSeat.plug_id ?? '',
              is_console: editingSeat.is_console,
              notes: editingSeat.notes ?? '',
            }
          : null}
        zones={zones}
      />

      {/* Delete Confirmation Modal */}
      {confirmOpen && confirmSeatId && confirmSeatName && (
        <ConfirmationModal
          open={confirmOpen}
          onClose={() => {
            setConfirmOpen(false);
            setConfirmSeatId(null);
            setConfirmSeatName('');
          }}
          title="Delete Seat"
          message={`Are you sure you want to delete "${confirmSeatName}"? This action cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={handleDelete}
          isLoading={deleteSeat.isPending}
          variant="danger"
        />
      )}
    </div>
  );
}

export default SeatsTab;
