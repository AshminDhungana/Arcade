import { useState } from 'react';
import { Tabs } from '@/components/ui/Tabs';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { useEventSummary } from '@/api/events';
import { BracketView } from './BracketView';
import { EventSummaryPanel } from './EventSummaryPanel';
import { ParticipantsList } from './ParticipantsList';
import { RegisterParticipantModal } from './RegisterParticipantModal';

export function EventDetail({ eventId, onBack }: { eventId: string; onBack: () => void }) {
  const { data: summary, isLoading, isError, error, refetch } = useEventSummary(eventId);
  const [tab, setTab] = useState('bracket');
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400" role="status" aria-label="Loading event">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-700 border-t-blue-500" />
      </div>
    );
  }
  if (isError) {
    return <ErrorState message={error?.message ?? 'Failed to load event.'} onRetry={() => refetch()} />;
  }
  if (!summary) return null;

  const TABS = [
    { id: 'bracket', label: 'Bracket' },
    { id: 'summary', label: 'Summary' },
    { id: 'participants', label: 'Participants' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <Button variant="secondary" onClick={onBack}>← Back to events</Button>
          <h1 className="mt-2 text-2xl font-semibold text-white">{summary.event.name}</h1>
          <p className="text-sm text-slate-400">{summary.event.game_title}</p>
        </div>
      </div>

      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === 'bracket' && <BracketView summary={summary} eventId={eventId} />}
      {tab === 'summary' && <EventSummaryPanel summary={summary} />}
      {tab === 'participants' && (
        <ParticipantsList summary={summary} onRegister={() => setIsRegisterOpen(true)} />
      )}

      <RegisterParticipantModal
        open={isRegisterOpen}
        eventId={eventId}
        onClose={() => setIsRegisterOpen(false)}
      />
    </div>
  );
}
