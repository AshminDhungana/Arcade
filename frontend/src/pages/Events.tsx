import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { EmptyState } from '@/components/ui/EmptyState';
import { Plus } from 'lucide-react';
import { useEvents } from '@/api/events';
import { EventList } from '@/components/events/EventList';
import { EventDetail } from '@/components/events/EventDetail';
import { CreateEventModal } from '@/components/events/CreateEventModal';

export function EventsPage() {
  const { data: events, isLoading, isError, error, refetch } = useEvents();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  if (selectedEventId) {
    return (
      <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
        <EventDetail eventId={selectedEventId} onBack={() => setSelectedEventId(null)} />
      </main>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400" role="status" aria-label="Loading events">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-700 border-t-blue-500" />
        <span className="ml-3">Loading events…</span>
      </div>
    );
  }

  if (isError) {
    const isForbidden = (error as Error)?.message?.includes('403');
    return (
      <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
        <h1 className="text-2xl font-semibold text-white">Events</h1>
        <ErrorState
          message={isForbidden ? 'Admin access required to view events.' : (error?.message ?? 'Failed to load events.')}
          onRetry={() => refetch()}
        />
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-6xl space-y-6 p-4 sm:p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Events</h1>
        <Button variant="emerald" onClick={() => setIsCreateOpen(true)}>
          <Plus className="h-4 w-4" /> New Event
        </Button>
      </div>

      {events && events.length > 0 ? (
        <EventList events={events} onSelect={setSelectedEventId} />
      ) : (
        <EmptyState message="No events yet. Create one to start a tournament." />
      )}

      <CreateEventModal open={isCreateOpen} onClose={() => setIsCreateOpen(false)} />
    </main>
  );
}

export default EventsPage;
