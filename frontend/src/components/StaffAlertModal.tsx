import { useQueryClient } from '@tanstack/react-query';
import { BellRing } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { useAlertStore } from '@/store/alertStore';
import type { Seat } from '@/types/seat';

export function StaffAlertModal() {
  const alerts = useAlertStore((state) => state.alerts);
  const dismiss = useAlertStore((state) => state.dismiss);
  const queryClient = useQueryClient();

  const current = alerts[0];
  if (!current) return null;

  const seats = queryClient.getQueryData<Seat[]>(['seats']) ?? [];
  const seat = seats.find((s) => s.id === current.seat_id);
  const seatLabel = seat?.name ?? current.seat_id;
  const waiting = alerts.length - 1;

  return (
    <Modal
      open
      onClose={dismiss}
      title={current.message}
      footer={
        <Button onClick={dismiss}>
          OK, got it
        </Button>
      }
    >
      <div className="flex items-start gap-3">
        <BellRing className="size-6 shrink-0 text-destructive" aria-hidden="true" />
        <div>
          <p className="text-sm font-medium text-foreground">Seat: {seatLabel}</p>
          {waiting > 0 && (
            <p className="mt-1 text-sm text-muted-foreground">
              {waiting} more waiting
            </p>
          )}
        </div>
      </div>
    </Modal>
  );
}
