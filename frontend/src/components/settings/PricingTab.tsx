import { useState } from 'react';
import { Plus, Edit, Trash2 } from 'lucide-react';
import { useZones, useCreateZone, useUpdateZone, useDeleteZone } from '@/api/settings';
import { useDeviceTypes, useCreateDeviceType, useUpdateDeviceType, useDeleteDeviceType } from '@/api/settings';
import { formatPaise } from '@/hooks/useFormatPaise';
import { Button } from '@/components/ui/Button';
import { Table, Th, Td } from '@/components/ui/Table';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { toast } from '@/store/toastStore';
import type { Zone, DeviceType, PricingModel } from '@/types/settings';

const PRICING_MODEL_LABELS: Record<PricingModel, string> = {
  PER_MINUTE: 'Per Minute',
  FLAT_HOURLY: 'Flat Hourly',
  TIME_BLOCK: 'Time Block',
};

const PRICING_MODEL_VARIANTS: Record<PricingModel, string> = {
  PER_MINUTE: 'bg-blue-900/30 text-blue-300',
  FLAT_HOURLY: 'bg-emerald-900/30 text-emerald-300',
  TIME_BLOCK: 'bg-amber-900/30 text-amber-300',
};

interface ZoneFormData {
  name: string;
  rate_per_minute_paise: number;
  rate_per_hour_paise: number;
  pricing_model: PricingModel;
  block_minutes: number | null;
}

function pricingModelToFormData(zone: Zone): ZoneFormData {
  return {
    name: zone.name,
    rate_per_minute_paise: zone.rate_per_minute_paise,
    rate_per_hour_paise: zone.rate_per_hour_paise,
    pricing_model: zone.pricing_model,
    block_minutes: zone.block_minutes,
  };
}

function ZoneFormModal({
  open,
  onClose,
  title,
  initialData,
  onSubmit,
  isLoading,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  initialData: ZoneFormData | null;
  onSubmit: (data: ZoneFormData) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState<ZoneFormData>({
    name: '',
    rate_per_minute_paise: 0,
    rate_per_hour_paise: 0,
    pricing_model: 'PER_MINUTE',
    block_minutes: null,
  });

  const [errors, setErrors] = useState<Partial<Record<keyof ZoneFormData, string>>>({});

  const handleChange = (field: keyof ZoneFormData, value: string | number | null) => {
    setFormData((prev) => ({ ...prev, [field]: value as any }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof ZoneFormData, string>> = {};
    if (!formData.name.trim()) newErrors.name = 'Name is required';
    if (formData.rate_per_minute_paise < 0) newErrors.rate_per_minute_paise = 'Rate must be non-negative';
    if (formData.rate_per_hour_paise < 0) newErrors.rate_per_hour_paise = 'Rate must be non-negative';
    if (formData.pricing_model === 'TIME_BLOCK' && (!formData.block_minutes || formData.block_minutes <= 0)) {
      newErrors.block_minutes = 'Block minutes required for Time Block pricing';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    onSubmit(formData);
  };

  if (initialData) {
    setFormData(initialData);
  }

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          name="name"
          label="Zone Name"
          value={formData.name}
          onChange={(e) => handleChange('name', e.target.value)}
          error={errors.name ?? null}
          placeholder="e.g. VIP Zone"
          autoFocus
        />

        <Input
          name="rate_per_minute_paise"
          label="Rate per Minute (₹)"
          type="number"
          step="0.01"
          min="0"
          value={formData.rate_per_minute_paise === 0 ? '' : (formData.rate_per_minute_paise / 100).toFixed(2)}
          onChange={(e) => {
            const val = e.target.value === '' ? 0 : Math.round(Number(e.target.value) * 100);
            handleChange('rate_per_minute_paise', val);
          }}
          error={errors.rate_per_minute_paise ?? null}
          placeholder="0.00"
        />

        <Input
          name="rate_per_hour_paise"
          label="Rate per Hour (₹)"
          type="number"
          step="0.01"
          min="0"
          value={formData.rate_per_hour_paise === 0 ? '' : (formData.rate_per_hour_paise / 100).toFixed(2)}
          onChange={(e) => {
            const val = e.target.value === '' ? 0 : Math.round(Number(e.target.value) * 100);
            handleChange('rate_per_hour_paise', val);
          }}
          error={errors.rate_per_hour_paise ?? null}
          placeholder="0.00"
        />

        <div>
          <label htmlFor="pricing_model" className="mb-1 block text-sm font-medium text-slate-300">
            Pricing Model
          </label>
          <select
            id="pricing_model"
            value={formData.pricing_model}
            onChange={(e) => handleChange('pricing_model', e.target.value as PricingModel)}
            className="w-full rounded-lg border border-slate-600 bg-slate-700 py-2.5 px-3 pr-8 text-sm text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            aria-invalid={!!errors.pricing_model}
          >
            <option value="PER_MINUTE">Per Minute</option>
            <option value="FLAT_HOURLY">Flat Hourly</option>
            <option value="TIME_BLOCK">Time Block</option>
          </select>
        </div>

        {(formData.pricing_model === 'TIME_BLOCK' || formData.block_minutes) && (
          <Input
            name="block_minutes"
            label="Block Minutes"
            type="number"
            min="1"
            value={formData.block_minutes === null ? '' : String(formData.block_minutes)}
            onChange={(e) => {
              const val = e.target.value === '' ? null : Number(e.target.value);
              handleChange('block_minutes', val);
            }}
            error={errors.block_minutes ?? null}
            placeholder="e.g. 30"
          />
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="emerald" loading={isLoading}>
            {initialData ? 'Save' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function DeviceTypeFormModal({
  open,
  onClose,
  title,
  initialData,
  onSubmit,
  isLoading,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  initialData: { name: string; description: string } | null;
  onSubmit: (data: { name: string; description: string }) => void;
  isLoading: boolean;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<{ name?: string }>({});

  if (initialData) {
    setName(initialData.name);
    setDescription(initialData.description || '');
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrors({ name: 'Name is required' });
      return;
    }
    setErrors({});
    onSubmit({ name: name.trim(), description: description.trim() });
  };

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          name="name"
          label="Device Type Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          error={errors.name}
          placeholder="e.g. PC, Console, VR"
          autoFocus
        />
        <Input
          name="description"
          label="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional description"
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="emerald" loading={isLoading}>
            {initialData ? 'Save' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function PricingTab() {
  const [zoneModalOpen, setZoneModalOpen] = useState(false);
  const [editingZone, setEditingZone] = useState<Zone | null>(null);
  const [deleteZoneId, setDeleteZoneId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const [deviceTypeModalOpen, setDeviceTypeModalOpen] = useState(false);
  const [editingDeviceType, setEditingDeviceType] = useState<DeviceType | null>(null);
  const [deleteDeviceTypeId, setDeleteDeviceTypeId] = useState<string | null>(null);

  const { data: zones = [], isLoading: zonesLoading, isError: zonesError, refetch: refetchZones } = useZones();
  const createZone = useCreateZone();
  const updateZone = useUpdateZone();
  const deleteZone = useDeleteZone();

  const { data: deviceTypes = [], isLoading: dtLoading, isError: dtError, refetch: refetchDeviceTypes } = useDeviceTypes();
  const createDeviceType = useCreateDeviceType();
  const updateDeviceType = useUpdateDeviceType();
  const deleteDeviceType = useDeleteDeviceType();

  const handleZoneSubmit = async (data: ZoneFormData) => {
    try {
      if (editingZone) {
        await updateZone.mutateAsync({ id: editingZone.id, data });
        toast.success('Zone updated successfully');
      } else {
        await createZone.mutateAsync(data);
        toast.success('Zone created successfully');
      }
      setZoneModalOpen(false);
      setEditingZone(null);
      refetchZones();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to save zone';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    }
  };

  const handleZoneDelete = async () => {
    if (!deleteZoneId) return;
    try {
      await deleteZone.mutateAsync(deleteZoneId);
      toast.success('Zone deleted');
      refetchZones();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete zone';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    } finally {
      setDeleteZoneId(null);
      setConfirmDelete(false);
    }
  };

  const openZoneModal = (zone?: Zone) => {
    setEditingZone(zone ?? null);
    setZoneModalOpen(true);
  };

  const handleDeviceTypeSubmit = async (data: { name: string; description: string }) => {
    try {
      if (editingDeviceType) {
        await updateDeviceType.mutateAsync({ id: editingDeviceType.id, data });
        toast.success('Device type updated');
      } else {
        await createDeviceType.mutateAsync(data);
        toast.success('Device type created');
      }
      setDeviceTypeModalOpen(false);
      setEditingDeviceType(null);
      refetchDeviceTypes();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to save device type';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    }
  };

  const handleDeviceTypeDelete = async () => {
    if (!deleteDeviceTypeId) return;
    try {
      await deleteDeviceType.mutateAsync(deleteDeviceTypeId);
      toast.success('Device type deleted');
      refetchDeviceTypes();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete device type';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    } finally {
      setDeleteDeviceTypeId(null);
    }
  };

  if (zonesLoading || dtLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold text-white">Pricing</h1>
        </div>
        <div className="flex h-64 items-center justify-center text-slate-400">Loading…</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-white">Pricing</h1>

      {/* Zones Section */}
      <section className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Zones</h2>
          <Button variant="emerald" onClick={() => openZoneModal()}>
            <Plus className="h-4 w-4 mr-2" />
            Add Zone
          </Button>
        </div>

        {zonesError && <ErrorState message="Failed to load zones. Admin required." />}

        {zones.length === 0 ? (
          <EmptyState message="No zones configured. Add one to get started." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-slate-700">
                <Th className="text-left">Name</Th>
                <Th className="text-right">Rate / Min</Th>
                <Th className="text-right">Rate / Hour</Th>
                <Th className="text-left">Pricing Model</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {zones.map((zone) => (
                <tr key={zone.id} className="border-b border-slate-800 hover:bg-slate-800/50">
                  <Td className="font-medium">{zone.name}</Td>
                  <Td className="text-right font-mono tabular-nums text-emerald-400">
                    {formatPaise(zone.rate_per_minute_paise)}
                  </Td>
                  <Td className="text-right font-mono tabular-nums text-emerald-400">
                    {formatPaise(zone.rate_per_hour_paise)}
                  </Td>
                  <Td>
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        PRICING_MODEL_VARIANTS[zone.pricing_model]
                      }`}
                    >
                      {PRICING_MODEL_LABELS[zone.pricing_model]}
                    </span>
                  </Td>
                  <Td className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="secondary"
                        aria-label={`Edit ${zone.name}`}
                        onClick={() => openZoneModal(zone)}
                        disabled={updateZone.isPending}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="danger"
                        aria-label={`Delete ${zone.name}`}
                        onClick={() => {
                          setDeleteZoneId(zone.id);
                          setConfirmDelete(true);
                        }}
                        disabled={deleteZone.isPending}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}

        {/* Zone Modal */}
        <ZoneFormModal
          open={zoneModalOpen}
          onClose={() => {
            setZoneModalOpen(false);
            setEditingZone(null);
          }}
          title={editingZone ? 'Edit Zone' : 'Create Zone'}
          initialData={editingZone ? pricingModelToFormData(editingZone) : null}
          onSubmit={handleZoneSubmit}
          isLoading={createZone.isPending || updateZone.isPending}
        />

        {/* Delete Confirmation Modal */}
        {confirmDelete && deleteZoneId && (
          <Modal
            open={confirmDelete}
            onClose={() => {
              setConfirmDelete(false);
              setDeleteZoneId(null);
            }}
            title="Delete Zone"
          >
            <p className="mb-4 text-slate-300">Are you sure you want to delete this zone? This action cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => { setConfirmDelete(false); setDeleteZoneId(null); }}>
                Cancel
              </Button>
              <Button variant="danger" onClick={handleZoneDelete} loading={deleteZone.isPending}>
                Delete
              </Button>
            </div>
          </Modal>
        )}
      </section>

      {/* Device Types Section */}
      <section className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Device Types</h2>
          <Button variant="emerald" onClick={() => { setEditingDeviceType(null); setDeviceTypeModalOpen(true); }}>
            <Plus className="h-4 w-4 mr-2" />
            Add Device Type
          </Button>
        </div>

        {dtError && <ErrorState message="Failed to load device types. Admin required." />}

        {deviceTypes.length === 0 ? (
          <EmptyState message="No device types yet. Add one to get started." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-slate-700">
                <Th className="text-left">Name</Th>
                <Th className="text-left">Description</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {deviceTypes.map((dt) => (
                <tr key={dt.id} className="border-b border-slate-800 hover:bg-slate-800/50">
                  <Td className="font-medium">{dt.name}</Td>
                  <Td className="text-slate-400">{dt.description ?? '—'}</Td>
                  <Td className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="secondary"
                        aria-label={`Edit ${dt.name}`}
                        onClick={() => { setEditingDeviceType(dt); setDeviceTypeModalOpen(true); }}
                        disabled={updateDeviceType.isPending}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="danger"
                        aria-label={`Delete ${dt.name}`}
                        onClick={() => { setDeleteDeviceTypeId(dt.id); }}
                        disabled={deleteDeviceType.isPending}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}

        {/* Device Type Modal */}
        <DeviceTypeFormModal
          open={deviceTypeModalOpen}
          onClose={() => { setDeviceTypeModalOpen(false); setEditingDeviceType(null); }}
          title={editingDeviceType ? 'Edit Device Type' : 'Create Device Type'}
          initialData={editingDeviceType ? { name: editingDeviceType.name, description: editingDeviceType.description ?? '' } : null}
          onSubmit={handleDeviceTypeSubmit}
          isLoading={createDeviceType.isPending || updateDeviceType.isPending}
        />

        {/* Delete Device Type Confirmation Modal */}
        {deleteDeviceTypeId && (
          <Modal
            open
            onClose={() => setDeleteDeviceTypeId(null)}
            title="Delete Device Type"
          >
            <p className="mb-4 text-slate-300">Are you sure you want to delete this device type? This action cannot be undone.</p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDeleteDeviceTypeId(null)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={handleDeviceTypeDelete} loading={deleteDeviceType.isPending}>
                Delete
              </Button>
            </div>
          </Modal>
        )}
      </section>
    </div>
  );
}

export default PricingTab;
