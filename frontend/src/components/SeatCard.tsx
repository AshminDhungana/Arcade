import type { Seat } from '@/types/seat';
import type { MouseEvent } from 'react';
import { SeatStatusBadge } from './SeatStatusBadge';
import { ElapsedTimer } from './ElapsedTimer';
import { Lock, Plus } from 'lucide-react';
import { useExtendSession } from '@/api/sessions';
import { toast } from '@/store/toastStore';

interface SeatCardProps {
  seat: Seat;
  onClick: (seat: Seat) => void;
}

/** A single seat card showing name, status badge, and live timer.
 *  Colour-coded border and hover state for interactivity. */
export function SeatCard({ seat, onClick }: SeatCardProps) {
  const isInUse = seat.status === 'IN_USE' || seat.status === 'PAUSED';
  const extendSession = useExtendSession();

  // Determine left border colour based on status
  const borderColor: Record<Seat['status'], string> = {
    AVAILABLE: 'border-l-emerald-500',
    IN_USE: 'border-l-orange-500',
    PAUSED: 'border-l-yellow-500',
    RESERVED: 'border-l-blue-500',
    MAINTENANCE: 'border-l-gray-500',
    OFFLINE: 'border-l-slate-500',
    BOOTING: 'border-l-blue-400',
    UNREACHABLE: 'border-l-red-500',
    EXPIRED: 'border-l-fuchsia-600',
  };

  // Epic 6.5.4: "Add time" is offered only for seats carrying an assigned limit
  // that are currently IN_USE or EXPIRED (and thus have a live session to extend).
  const hasLimit = Boolean(seat.assigned_end_at);
  const canAddTime =
    hasLimit &&
    (seat.status === 'IN_USE' || seat.status === 'EXPIRED') &&
    Boolean(seat.current_session_id);

  const handleAddTime = (e: MouseEvent) => {
    // SeatCard is a <button>; stop the add-time click from opening the seat modal.
    e.stopPropagation();
    if (!seat.current_session_id) return;
    const input = window.prompt('Add how many minutes?', '30');
    if (input === null) return;
    const minutes = Number(input);
    if (!Number.isFinite(minutes) || minutes <= 0) {
      toast.error('Enter a positive number of minutes');
      return;
    }
    extendSession.mutate(
      { session_id: seat.current_session_id, additional_minutes: minutes },
      {
        onSuccess: () => toast.success(`Added ${minutes} min to ${seat.name}`),
        onError: (err) => toast.error(err.message ?? 'Failed to add time'),
      },
    );
  };

  return (
    <button
      type="button"
      onClick={() => onClick(seat)}
      className={`w-full text-left rounded-lg border border-slate-700 border-l-4 ${borderColor[seat.status] ?? 'border-l-slate-400'} bg-slate-800 p-4 shadow-sm hover:bg-slate-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900`}
      aria-label={`Seat ${seat.name}, status ${seat.status}`}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-white">{seat.name}</h3>
        <div className="flex items-center gap-2">
          <SeatStatusBadge status={seat.status} />
          {seat.overlay_forced && (
            <span
              className="flex items-center gap-1 rounded-full bg-amber-900/50 px-2 py-0.5 text-xs font-medium text-amber-300 border border-amber-800"
              aria-label="Force overlay active"
            >
              <Lock className="h-3 w-3" role="img" aria-label="Lock" />
              Locked
            </span>
          )}
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between text-sm text-slate-400">
        <span>{seat.is_console ? 'Console' : 'PC'}</span>
        <div className="flex items-center gap-2">
          {canAddTime && (
            <span
              role="button"
              tabIndex={0}
              onClick={handleAddTime}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.stopPropagation();
                  handleAddTime(e);
                }
              }}
              className="flex items-center gap-1 rounded-md bg-fuchsia-600 px-2 py-1 text-xs font-medium text-white hover:bg-fuchsia-500 focus:outline-none focus:ring-2 focus:ring-fuchsia-400 cursor-pointer"
              aria-label={`Add time to ${seat.name}`}
            >
              <Plus className="h-3 w-3" /> Add time
            </span>
          )}
          {isInUse && (
            // Show live timer only when seat is IN_USE or PAUSED
            // Note: startedAt comes from session data (not yet wired in this feature)
            <ElapsedTimer startedAt={new Date().toISOString()} isRunning={seat.status === 'IN_USE'} />
          )}
        </div>
      </div>
    </button>
  );
}
