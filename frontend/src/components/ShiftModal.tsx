import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useCloseShift, useCurrentShift, useOpenShift } from '@/api/shifts';
import { useSettings } from '@/api/settings';
import { toast } from '@/store/toastStore';
import { formatPaise } from '@/hooks/useFormatPaise';

interface ShiftModalProps {
  open: boolean;
  onClose: () => void;
}

function parseRupeesToPaise(value: string): number {
  const amount = Number.parseFloat(value);
  if (Number.isNaN(amount) || amount < 0) return 0;
  return Math.round(amount * 100);
}

export function ShiftModal({ open, onClose }: ShiftModalProps) {
  const { data: current, isPending } = useCurrentShift();
  const openShift = useOpenShift();
  const closeShift = useCloseShift();
  const { data: settings } = useSettings();

  const [view, setView] = useState<'open' | 'live' | 'close'>('open');
  const [floatRupees, setFloatRupees] = useState('');
  const [countedRupees, setCountedRupees] = useState('');

  const rawThreshold = settings?.shift_cash_variance_threshold;
  const parsedThreshold = rawThreshold ? Number.parseInt(rawThreshold, 10) : 5000;
  const thresholdPaise = Number.isNaN(parsedThreshold) ? 5000 : parsedThreshold;

  const countedPaise = parseRupeesToPaise(countedRupees);
  const expectedPaise = current?.expected_cash_paise ?? 0;
  const variancePaise = countedPaise - expectedPaise;
  const varianceFlagged = Math.abs(variancePaise) > thresholdPaise;

  const handleOpen = () => {
    openShift.mutate(parseRupeesToPaise(floatRupees), {
      onSuccess: () => {
        toast.success('Shift opened');
        setView('live');
        setFloatRupees('');
      },
      onError: (err) => toast.error(err.message ?? 'Failed to open shift'),
    });
  };

  const handleClose = () => {
    closeShift.mutate(countedPaise, {
      onSuccess: () => {
        toast.success('Shift closed');
        setView('open');
        setCountedRupees('');
        onClose();
      },
      onError: (err) => toast.error(err.message ?? 'Failed to close shift'),
    });
  };

  const goToClose = () => {
    setCountedRupees((expectedPaise / 100).toFixed(2));
    setView('close');
  };

  if (isPending) {
    return (
      <Modal open={open} onClose={onClose} title="Shift">
        <p className="text-sm text-muted-foreground">Loading shift…</p>
      </Modal>
    );
  }

  if (current === null) {
    return (
      <Modal open={open} onClose={onClose} title="Shift">
        <div className="space-y-4">
          <Input
            id="float-rupees"
            label="Cash float (₹)"
            type="number"
            min="0"
            step="0.01"
            value={floatRupees}
            onChange={(e) => setFloatRupees(e.target.value)}
            placeholder="0.00"
          />
          <Button
            onClick={handleOpen}
            loading={openShift.isPending}
            disabled={openShift.isPending}
            className="w-full"
          >
            Open Shift
          </Button>
        </div>
      </Modal>
    );
  }

  if (view === 'close') {
    return (
      <Modal open={open} onClose={onClose} title="Close Shift">
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Expected cash: {formatPaise(expectedPaise)}
          </p>
          <Input
            id="counted-rupees"
            label="Counted cash (₹)"
            type="number"
            min="0"
            step="0.01"
            value={countedRupees}
            onChange={(e) => setCountedRupees(e.target.value)}
          />
          {countedRupees !== '' && (
            <p
              className={`text-sm ${varianceFlagged ? 'text-destructive' : 'text-muted-foreground'}`}
            >
              Variance: {variancePaise >= 0 ? '+' : ''}
              {formatPaise(Math.abs(variancePaise))}
            </p>
          )}
          {varianceFlagged && (
            <p
              role="alert"
              className="rounded-md bg-destructive/15 p-3 text-sm text-destructive"
            >
              Variance exceeds the threshold of {formatPaise(thresholdPaise)}.
            </p>
          )}
          <Button
            variant="danger"
            onClick={handleClose}
            loading={closeShift.isPending}
            disabled={closeShift.isPending}
            className="w-full"
          >
            Close Shift
          </Button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal open={open} onClose={onClose} title="Shift">
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Opened with {formatPaise(current.shift.float_paise)} on{' '}
          {new Date(current.shift.opened_at).toLocaleString()}
        </p>
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-secondary/50 p-3">
            <p className="text-xs text-muted-foreground">Revenue</p>
            <p className="text-lg font-bold">
              {formatPaise(current.total_revenue_paise)}
            </p>
          </div>
          <div className="rounded-lg bg-secondary/50 p-3">
            <p className="text-xs text-muted-foreground">Sessions</p>
            <p className="text-lg font-bold">{current.session_count}</p>
          </div>
          <div className="rounded-lg bg-secondary/50 p-3">
            <p className="text-xs text-muted-foreground">Avg duration</p>
            <p className="text-lg font-bold">
              {Math.round(current.average_duration_seconds / 60)} min
            </p>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          Expected cash: {formatPaise(current.expected_cash_paise)}
        </p>
        <Button onClick={goToClose} className="w-full">
          Close Shift
        </Button>
      </div>
    </Modal>
  );
}
