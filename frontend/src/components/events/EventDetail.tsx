import { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { useEventSummary } from '@/api/events';
import { BracketView } from './BracketView';
import { EventSummaryPanel } from './EventSummaryPanel';
import { ParticipantsList } from './ParticipantsList';
import { RegisterParticipantModal } from './RegisterParticipantModal';

export function EventDetail({ eventId, onBack }: { eventId: string; onBack: () => void }) {
  const { data: summary, isLoading, isError, error, refetch } = useEventSummary(eventId);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-muted-foreground" role="status" aria-label="Loading event">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-primary" />
      </div>
    );
  }
  if (isError) {
    return <ErrorState message={error?.message ?? 'Failed to load event.'} onRetry={() => refetch()} />;
  }
  if (!summary) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <Button variant="secondary" onClick={onBack}>← Back to events</Button>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">{summary.event.name}</h1>
          <p className="text-sm text-muted-foreground">{summary.event.game_title}</p>
        </div>
      </div>

      <Tabs defaultValue="bracket">
        <TabsList>
          <TabsTrigger value="bracket">Bracket</TabsTrigger>
          <TabsTrigger value="summary">Summary</TabsTrigger>
          <TabsTrigger value="participants">Participants</TabsTrigger>
        </TabsList>
        <TabsContent value="bracket"><BracketView summary={summary} eventId={eventId} /></TabsContent>
        <TabsContent value="summary"><EventSummaryPanel summary={summary} /></TabsContent>
        <TabsContent value="participants"><ParticipantsList summary={summary} onRegister={() => setIsRegisterOpen(true)} /></TabsContent>
      </Tabs>

      <RegisterParticipantModal
        open={isRegisterOpen}
        eventId={eventId}
        onClose={() => setIsRegisterOpen(false)}
      />
    </div>
  );
}
