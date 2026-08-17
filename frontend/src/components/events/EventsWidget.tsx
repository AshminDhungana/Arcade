import { Link } from 'react-router-dom';
import { Calendar, Trophy, Users, ArrowRight } from 'lucide-react';
import { useEvents } from '@/api/events';
import { formatPaise, formatDateTime } from '@/hooks/useFormatPaise';

export function EventsWidget() {
  const { data: events, isLoading } = useEvents();
  const upcoming = events
    ?.filter((e) => e.status === 'UPCOMING')
    .sort((a, b) => new Date(a.event_date).getTime() - new Date(b.event_date).getTime());

  if (isLoading) {
    return (
      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-medium text-foreground">Upcoming Events</h3>
        </div>
        <div className="h-8 w-full animate-pulse rounded bg-muted" />
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-medium text-foreground">Upcoming Events</h3>
        <Link to="/events" className="text-sm text-primary hover:underline flex items-center gap-1">
          View All <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {upcoming && upcoming.length > 0 ? (
        <div className="space-y-3">
          {upcoming.map((event) => (
            <div key={event.id} className="rounded-md border border-border p-3 hover:bg-muted/50 transition-colors">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <span className="text-lg">🎮</span>
                    <span className="truncate">{event.name}</span>
                    <span className="text-muted-foreground whitespace-nowrap">{event.game_title}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {formatDateTime(event.event_date)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Trophy className="h-3 w-3" />
                      {formatPaise(event.prize_pool_paise)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="h-3 w-3" />
                      ₹{event.entry_fee_paise / 100}
                    </span>
                    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-success/10 text-success">
                      {event.status}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground text-center py-4">
          No upcoming events. Create one on the <Link to="/events" className="text-primary hover:underline">Events page</Link>.
        </p>
      )}
    </div>
  );
}
