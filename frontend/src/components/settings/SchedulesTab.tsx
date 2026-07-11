import { useState } from 'react';
import { Plus, Edit, Trash2 } from 'lucide-react';
import {
  useSchedules,
  useCreateSchedule,
  useUpdateSchedule,
  useDeleteSchedule,
} from '@/api/settings';
import { formatPaise } from '@/hooks/useFormatPaise';
import { Button } from '@/components/ui/Button';
import { Table, Th, Td } from '@/components/ui/Table';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Switch } from '@/components/ui/Switch';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { toast } from '@/store/toastStore';
import type { PeakSchedule } from '@/types/settings';

const DAY_OPTIONS = [
  { value: 'all', label: 'All days' },
  { value: '0', label: 'Sunday' },
  { value: '1', label: 'Monday' },
  { value: '2', label: 'Tuesday' },
  { value: '3', label: 'Wednesday' },
  { value: '4', label: 'Thursday' },
  { value: '5', label: 'Friday' },
  { value: '6', label: 'Saturday' },
];

function dayOfWeekLabel(day: number | null): string {
  if (day === null) return 'All days';
  return DAY_OPTIONS.find((d) => d.value === String(day))?.label ?? 'Unknown';
}

function peakBadge(isPeak: boolean) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        isPeak
          ? 'bg-amber-900/30 text-amber-300'
          : 'bg-blue-900/30 text-blue-300'
      }`}
    >
      {isPeak ? 'Peak' : 'Off-Peak'}
    </span>
  );
}

interface ScheduleFormData {
  name: string;
  is_peak: boolean;
  day_of_week: number | null;
  start_time: string;
  end_time: string;
  surcharge_paise: number;
}

function scheduleToFormData(schedule: PeakSchedule): ScheduleFormData {
  return {
    name: schedule.name,
    is_peak: schedule.is_peak,
    day_of_week: schedule.day_of_week,
    start_time: schedule.start_time,
    end_time: schedule.end_time,
    surcharge_paise: schedule.surcharge_paise,
  };
}

function ScheduleFormModal({
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
  initialData: ScheduleFormData | null;
  onSubmit: (data: ScheduleFormData) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState<ScheduleFormData>({
    name: '',
    is_peak: false,
    day_of_week: null,
    start_time: '',
    end_time: '',
    surcharge_paise: 0,
  });

  const [errors, setErrors] = useState<Partial<Record<keyof ScheduleFormData, string>>>({});

  const handleChange = (
    field: keyof ScheduleFormData,
    value: string | number | boolean | null,
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }) as typeof prev);
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof ScheduleFormData, string>> = {};
    if (!formData.name.trim()) newErrors.name = 'Name is required';
    if (!formData.start_time) newErrors.start_time = 'Start time is required';
    if (!formData.end_time) newErrors.end_time = 'End time is required';
    if (formData.start_time && formData.end_time && formData.start_time >= formData.end_time) {
      newErrors.end_time = 'End time must be after start time';
    }
    if (formData.surcharge_paise < 0) newErrors.surcharge_paise = 'Surcharge must be non-negative';
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
          label="Schedule Name"
          value={formData.name}
          onChange={(e) => handleChange('name', e.target.value)}
          error={errors.name ?? null}
          placeholder="e.g. Weekend Peak"
          autoFocus
        />

        <div>
          <Switch
            checked={formData.is_peak}
            onCheckedChange={(v) => handleChange('is_peak', v)}
            label="Peak Schedule"
            description="Off-Peak when off"
          />
        </div>

        <div>
          <label htmlFor="day_of_week" className="mb-1 block text-sm font-medium text-slate-300">
            Day of Week
          </label>
          <select
            id="day_of_week"
            value={formData.day_of_week === null ? 'all' : String(formData.day_of_week)}
            onChange={(e) => {
              const val = e.target.value;
              handleChange('day_of_week', val === 'all' ? null : Number(val));
            }}
            className="w-full rounded-lg border border-slate-600 bg-slate-700 py-2.5 px-3 pr-8 text-sm text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            aria-invalid={!!errors.day_of_week}
          >
            <option value="all">All days</option>
            {DAY_OPTIONS.filter((d) => d.value !== 'all').map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
          {errors.day_of_week && (
            <p role="alert" className="mt-1 flex items-center gap-1 text-xs text-red-400">
              {errors.day_of_week}
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Input
            name="start_time"
            label="Start Time (HH:MM)"
            type="time"
            value={formData.start_time}
            onChange={(e) => handleChange('start_time', e.target.value)}
            error={errors.start_time ?? null}
            placeholder="18:00"
          />
          <Input
            name="end_time"
            label="End Time (HH:MM)"
            type="time"
            value={formData.end_time}
            onChange={(e) => handleChange('end_time', e.target.value)}
            error={errors.end_time ?? null}
            placeholder="23:59"
          />
        </div>

        <Input
          name="surcharge_paise"
          label="Surcharge per Hour (₹)"
          type="number"
          step="0.01"
          min="0"
          value={formData.surcharge_paise === 0 ? '' : (formData.surcharge_paise / 100).toFixed(2)}
          onChange={(e) => {
            const val = e.target.value === '' ? 0 : Math.round(Number(e.target.value) * 100);
            handleChange('surcharge_paise', val);
          }}
          error={errors.surcharge_paise ?? null}
          placeholder="0.00"
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

export function SchedulesTab() {
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<PeakSchedule | null>(null);
  const [deleteScheduleId, setDeleteScheduleId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data: schedules = [], isLoading, isError, refetch } = useSchedules();
  const createSchedule = useCreateSchedule();
  const updateSchedule = useUpdateSchedule();
  const deleteSchedule = useDeleteSchedule();

  const handleSubmit = async (data: ScheduleFormData) => {
    try {
      if (editingSchedule) {
        await updateSchedule.mutateAsync({ id: editingSchedule.id, data });
        toast.success('Schedule updated successfully');
      } else {
        await createSchedule.mutateAsync(data);
        toast.success('Schedule created successfully');
      }
      setModalOpen(false);
      setEditingSchedule(null);
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to save schedule';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    }
  };

  const handleDelete = async () => {
    if (!deleteScheduleId) return;
    try {
      await deleteSchedule.mutateAsync(deleteScheduleId);
      toast.success('Schedule deleted');
      refetch();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete schedule';
      if (msg.includes('403') || msg.includes('401')) {
        toast.error('Admin required');
      } else {
        toast.error(msg);
      }
    } finally {
      setDeleteScheduleId(null);
      setConfirmDelete(false);
    }
  };

  const openModal = (schedule?: PeakSchedule) => {
    setEditingSchedule(schedule ?? null);
    setModalOpen(true);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold text-white">Schedules</h1>
        </div>
        <div className="flex h-64 items-center justify-center text-slate-400">Loading…</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-white">Schedules</h1>
        <Button variant="emerald" onClick={() => openModal()}>
          <Plus className="h-4 w-4 mr-2" />
          Add Schedule
        </Button>
      </div>

      {isError && <ErrorState message="Failed to load schedules. Admin required." onRetry={refetch} />}

      <section className="rounded-xl border border-slate-700 bg-slate-800 p-5">
        {schedules.length === 0 ? (
          <EmptyState message="No schedules configured. Add one to get started." />
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-slate-700">
                <Th className="text-left">Name</Th>
                <Th className="text-left">Type</Th>
                <Th className="text-left">Days</Th>
                <Th className="text-left">Time Window</Th>
                <Th className="text-right">Surcharge / Hour</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((schedule) => (
                <tr key={schedule.id} className="border-b border-slate-800 hover:bg-slate-800/50">
                  <Td className="font-medium">{schedule.name}</Td>
                  <Td>{peakBadge(schedule.is_peak)}</Td>
                  <Td className="text-slate-300">{dayOfWeekLabel(schedule.day_of_week)}</Td>
                  <Td className="font-mono tabular-nums">{schedule.start_time}–{schedule.end_time}</Td>
                  <Td className="text-right font-mono tabular-nums text-emerald-400">
                    {formatPaise(schedule.surcharge_paise)}
                  </Td>
                  <Td className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="secondary"
                        aria-label={`Edit ${schedule.name}`}
                        onClick={() => openModal(schedule)}
                        disabled={updateSchedule.isPending}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="danger"
                        aria-label={`Delete ${schedule.name}`}
                        onClick={() => {
                          setDeleteScheduleId(schedule.id);
                          setConfirmDelete(true);
                        }}
                        disabled={deleteSchedule.isPending}
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
      </section>

      {/* Create/Edit Modal */}
      <ScheduleFormModal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditingSchedule(null);
        }}
        title={editingSchedule ? 'Edit Schedule' : 'Create Schedule'}
        initialData={editingSchedule ? scheduleToFormData(editingSchedule) : null}
        onSubmit={handleSubmit}
        isLoading={createSchedule.isPending || updateSchedule.isPending}
      />

      {/* Delete Confirmation Modal */}
      {confirmDelete && deleteScheduleId && (
        <Modal
          open={confirmDelete}
          onClose={() => {
            setConfirmDelete(false);
            setDeleteScheduleId(null);
          }}
          title="Delete Schedule"
        >
          <p className="mb-4 text-slate-300">
            Are you sure you want to delete this schedule? This action cannot be undone.
          </p>
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                setConfirmDelete(false);
                setDeleteScheduleId(null);
              }}
            >
              Cancel
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={deleteSchedule.isPending}>
              Delete
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}

export default SchedulesTab;
