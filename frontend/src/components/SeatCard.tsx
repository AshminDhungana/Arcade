import type { Seat } from '@/types/seat';
import { SeatStatusBadge } from './SeatStatusBadge';
import { ElapsedTimer } from './ElapsedTimer';

interface SeatCardProps {
  seat: Seat;
  onClick: (seat: Seat) => void;
}

/** A single seat card showing name, status badge, and live timer.
 *  Colour-coded border and hover state for interactivity. */
export function SeatCard({ seat, onClick }: SeatCardProps) {
  const isInUse = seat.status === 'IN_USE' || seat.status === 'PAUSED';

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
        <SeatStatusBadge status={seat.status} />
      </div>

      <div className="mt-2 flex items-center justify-between text-sm text-slate-400">
        <span>{seat.is_console ? 'Console' : 'PC'}</span>
        {isInUse && (
          // Show live timer only when seat is IN_USE or PAUSED
          // Note: startedAt comes from session data (not yet wired in this feature)
          <ElapsedTimer startedAt={new Date().toISOString()} isRunning={seat.status === 'IN_USE'} />
        )}
      </div>
    </button>
  );
}
