import { SeatStatus } from '@/types/seat';

/** Maps each SeatStatus to its colour Tailwind class. */
const STATUS_BG: Record<SeatStatus, string> = {
  AVAILABLE: 'bg-emerald-500',
  IN_USE: 'bg-orange-500',
  PAUSED: 'bg-yellow-500',
  RESERVED: 'bg-blue-500',
  MAINTENANCE: 'bg-gray-500',
  OFFLINE: 'bg-slate-500',
  BOOTING: 'bg-blue-400',
  UNREACHABLE: 'bg-red-500',
  EXPIRED: 'bg-fuchsia-600',
};

/** Maps each SeatStatus to a human-readable label. */
const STATUS_LABEL: Record<SeatStatus, string> = {
  AVAILABLE: 'Available',
  IN_USE: 'In Use',
  PAUSED: 'Paused',
  RESERVED: 'Reserved',
  MAINTENANCE: 'Maintenance',
  OFFLINE: 'Offline',
  BOOTING: 'Booting',
  UNREACHABLE: 'Unreachable',
  EXPIRED: 'Expired',
};

interface SeatStatusBadgeProps {
  status: SeatStatus;
}

/** Reusable status badge with colour coding.
 *  Renders a small rounded dot + status text label. */
export function SeatStatusBadge({ status }: SeatStatusBadgeProps) {
  const bg = STATUS_BG[status] ?? 'bg-slate-400';
  const label = STATUS_LABEL[status] ?? status;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium text-white bg-slate-700"
      aria-label={`Seat status: ${status}`}
    >
      <span className={`inline-block h-2 w-2 rounded-full ${bg}`} />
      {label}
    </span>
  );
}
