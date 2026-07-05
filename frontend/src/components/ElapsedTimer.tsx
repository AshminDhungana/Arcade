import { useState, useEffect, useCallback } from 'react';

interface ElapsedTimerProps {
  /** ISO string of when the session started. */
  startedAt: string;
  /** Whether the timer should tick. Default: true. */
  isRunning?: boolean;
}

/** Format a number of seconds as HH:MM:SS. */
function formatElapsed(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

/** Live elapsed timer that ticks every second while `isRunning` is true. */
export function ElapsedTimer({ startedAt, isRunning = true }: ElapsedTimerProps) {
  const start = new Date(startedAt).getTime();

  const calculateElapsed = useCallback(() => {
    return Math.max(0, Math.floor((Date.now() - start) / 1000));
  }, [start]);

  const [elapsed, setElapsed] = useState<number>(calculateElapsed);

  useEffect(() => {
    if (!isRunning) {
      // Reset to 0 when paused/not running
      setElapsed(0);
      return;
    }

    // Update elapsed every second
    const intervalId = setInterval(() => {
      setElapsed(calculateElapsed());
    }, 1000);

    return () => clearInterval(intervalId);
  }, [isRunning, startedAt, start, calculateElapsed]);

  return (
    <span aria-label="Elapsed time" className="font-mono text-lg" title="Elapsed session time">
      {formatElapsed(elapsed)}
    </span>
  );
}
