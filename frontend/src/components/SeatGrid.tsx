import { useState } from 'react';
import type { Seat } from '@/types/seat';
import { useSeats } from '@/api/seats';
import { SeatCard } from './SeatCard';
import { SeatActionModal } from './SeatActionModal';
import { SessionDrawer } from './SessionDrawer';

/** Displays all available seats in a responsive grid.
 *  Subscribes to WebSocket updates via the `seat_updated` event,
 *  which invalidates the `['seats']` query in `useSeats`. */
export function SeatGrid() {
  const { data: seats, isLoading, isError, error } = useSeats();
  const [selectedSeat, setSelectedSeat] = useState<Seat | null>(null);
  const [drawerSeat, setDrawerSeat] = useState<Seat | null>(null);

  const handleSeatClick = (seat: Seat) => {
    if (seat.status === 'IN_USE' && seat.current_session_id) {
      setDrawerSeat(seat);
    } else {
      setSelectedSeat(seat);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400" role="status" aria-label="Loading seats">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-700 border-t-blue-500"></div>
        <span className="ml-3">Loading seats…</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg bg-red-900/20 p-4 text-red-300 border border-red-800" role="alert">
        <p className="font-medium">Failed to load seats</p>
        <p className="text-sm text-red-400 mt-1">{error?.message ?? 'Unknown error'}</p>
      </div>
    );
  }

  const sortedSeats = [...(seats ?? [])].sort((a, b) => a.name.localeCompare(b.name));

  return (
    <>
      <div
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
        role="list"
        aria-label="Seat grid"
      >
        {sortedSeats.map((seat) => (
          <SeatCard key={seat.id} seat={seat} onClick={handleSeatClick} />
        ))}
      </div>

      {selectedSeat && (
        <SeatActionModal
          seat={selectedSeat}
          onClose={() => setSelectedSeat(null)}
        />
      )}

      {drawerSeat && drawerSeat.current_session_id && (
        <SessionDrawer
          seat={drawerSeat}
          sessionId={drawerSeat.current_session_id}
          onClose={() => setDrawerSeat(null)}
        />
      )}
    </>
  );
}
