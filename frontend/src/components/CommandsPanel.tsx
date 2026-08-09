import { useState } from 'react';
import { Loader2, Pause, Play, Lock, Unlock } from 'lucide-react';
import type { Seat } from '@/types/seat';
import { forceOverlay, useSeat } from '@/api/seats';
import { usePauseSession, useResumeSession } from '@/api/sessions';
import { useAuthStore } from '@/store/authStore';
import { toast } from '@/store/toastStore';

interface CommandsPanelProps {
  seat: Seat;
  sessionId: string;
}

/** Remote controls for an in-flight session. Pause/resume the running timer
 *  (cashier+) and, for admins, force the kiosk overlay on/off. */
export function CommandsPanel({ seat, sessionId }: CommandsPanelProps) {
  const { data: liveSeat } = useSeat(seat.id, { initialData: seat });
  const currentSeat = liveSeat ?? seat;
  const isAdmin = useAuthStore((s) => s.staff?.role === 'ADMIN');

  const pauseSession = usePauseSession();
  const resumeSession = useResumeSession();
  const [overlayLoading, setOverlayLoading] = useState<'on' | 'off' | null>(null);

  const isPaused = currentSeat.status === 'PAUSED';
  const isInUse = currentSeat.status === 'IN_USE';
  const timerEnabled = isInUse || isPaused;
  const timerBusy = pauseSession.isPending || resumeSession.isPending;
  const overlayBusy = overlayLoading !== null;

  const handlePause = () => {
    pauseSession.mutate(
      { session_id: sessionId },
      {
        onSuccess: () => toast.success('Session paused'),
        onError: (err) => toast.error(err.message ?? 'Failed to pause session'),
      },
    );
  };

  const handleResume = () => {
    resumeSession.mutate(
      { session_id: sessionId },
      {
        onSuccess: () => toast.success('Session resumed'),
        onError: (err) => toast.error(err.message ?? 'Failed to resume session'),
      },
    );
  };

  const handleForceOverlay = async (show: boolean) => {
    setOverlayLoading(show ? 'on' : 'off');
    try {
      await forceOverlay(currentSeat.id, show);
      toast.success(show ? 'Force overlay ON' : 'Force overlay OFF');
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setOverlayLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <section aria-label="Timer controls">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
          Timer
        </h3>
        <button
          type="button"
          onClick={isPaused ? handleResume : handlePause}
          disabled={!timerEnabled || timerBusy}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
        >
          {timerBusy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : isPaused ? (
            <Play className="h-4 w-4" />
          ) : (
            <Pause className="h-4 w-4" />
          )}
          {isPaused ? 'Resume Session' : 'Pause Session'}
        </button>
      </section>

      {isAdmin && (
        <section aria-label="Overlay controls">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Overlay
          </h3>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleForceOverlay(true)}
              disabled={overlayBusy}
              className="flex items-center justify-center gap-2 rounded-lg bg-slate-700 px-4 py-3 text-sm font-medium text-slate-100 transition-colors hover:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {overlayLoading === 'on' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Lock className="h-4 w-4" />
              )}
              Force Overlay On
            </button>
            <button
              type="button"
              onClick={() => handleForceOverlay(false)}
              disabled={overlayBusy}
              className="flex items-center justify-center gap-2 rounded-lg bg-slate-700 px-4 py-3 text-sm font-medium text-slate-100 transition-colors hover:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {overlayLoading === 'off' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Unlock className="h-4 w-4" />
              )}
              Force Overlay Off
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
