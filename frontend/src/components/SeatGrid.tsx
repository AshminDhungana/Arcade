import { useMemo, useState } from 'react';
import type { Seat } from '@/types/seat';
import { useSeats } from '@/api/seats';
import { SeatCard } from './SeatCard';
import { SeatActionModal } from './SeatActionModal';
import { SessionDrawer } from './SessionDrawer';

interface ZoneGroup {
  zoneId: string;
  zoneName: string;
  seats: Seat[];
}

/** Group seats by zone, labelling each group with its zone name.
 *
 * When several zones share a stored name (e.g. legacy duplicate "Main Floor"
 * zones), the section headers are disambiguated with a numeric suffix so they
 * stay scannable. Within a zone, identical seat names also get a suffix. */
function groupSeatsByZone(seats: Seat[]): ZoneGroup[] {
  const groups = new Map<string, ZoneGroup>();
  const headerCount = new Map<string, number>();

  for (const seat of seats) {
    let group = groups.get(seat.zone_id);
    if (!group) {
      let header = seat.zone_name ?? seat.zone_id;
      const seen = headerCount.get(header) ?? 0;
      if (seen > 0) header = `${header} (${seen + 1})`;
      headerCount.set(header, seen + 1);
      group = { zoneId: seat.zone_id, zoneName: header, seats: [] };
      groups.set(seat.zone_id, group);
    }
    group.seats.push(seat);
  }

  const ordered = [...groups.values()].sort((a, b) =>
    a.zoneName.localeCompare(b.zoneName),
  );
  for (const group of ordered) {
    // Sort within the zone, then disambiguate duplicate seat names.
    group.seats.sort((a, b) => a.name.localeCompare(b.name));
    const nameCount = new Map<string, number>();
    group.seats = group.seats.map((seat) => {
      const n = nameCount.get(seat.name) ?? 0;
      nameCount.set(seat.name, n + 1);
      return n === 0 ? seat : { ...seat, name: `${seat.name} (${n + 1})` };
    });
  }
  return ordered;
}

/** Displays seats grouped by zone in responsive grids.
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

  const groups = useMemo(() => groupSeatsByZone(seats ?? []), [seats]);

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

  return (
    <>
      <div className="space-y-8">
        {groups.map((group) => (
          <section key={group.zoneId} aria-label={`Zone ${group.zoneName}`}>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              {group.zoneName}
            </h2>
            <div
              className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
              role="list"
              aria-label={`Seats in ${group.zoneName}`}
            >
              {group.seats.map((seat) => (
                <SeatCard key={seat.id} seat={seat} onClick={handleSeatClick} />
              ))}
            </div>
          </section>
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
