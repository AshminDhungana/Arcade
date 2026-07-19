import { formatPaise } from '@/hooks/useFormatPaise';
import type { EventResponse } from '@/types/events';

const STATUS_STYLES: Record<string, string> = {
  UPCOMING: 'bg-blue-500', ACTIVE: 'bg-orange-500', COMPLETED: 'bg-emerald-500',
};

export function EventList({ events, onSelect }: { events: EventResponse[]; onSelect: (id: string) => void }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {events.map((e) => (
        <button
          key={e.id}
          type="button"
          onClick={() => onSelect(e.id)}
          className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 text-left transition-colors hover:border-foreground/30 focus:outline-none focus:ring-2 focus:ring-ring"
          aria-label={`Open event ${e.name}`}
        >
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-base font-medium text-foreground">{e.name}</h3>
            <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium text-white ${STATUS_STYLES[e.status]}`}>
              <span className="h-2 w-2 rounded-full bg-white/80" />{e.status}
            </span>
          </div>
          <p className="text-sm text-muted-foreground">{e.game_title}</p>
          <p className="text-sm text-muted-foreground">
            Prize pool: <span className="tabular-nums text-foreground">{formatPaise(e.prize_pool_paise)}</span>
          </p>
          <p className="text-xs text-muted-foreground">{e.bracket_type === 'SINGLE_ELIMINATION' ? 'Single elimination' : 'Double elimination'}</p>
        </button>
      ))}
    </div>
  );
}
