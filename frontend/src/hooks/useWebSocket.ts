import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useHealthStore } from '@/store/healthStore';
import type {
  WSMessage,
  WSStatus,
  SeatUpdatedPayload,
  HealthUpdatePayload,
  AnnouncementPayload,
  AlertPayload,
} from '@/types/ws';

// ---------------------------------------------------------------------------
// Constants (mirrors agent behaviour)
// ---------------------------------------------------------------------------

/** Initial reconnect delay in milliseconds. */
const INITIAL_RECONNECT_DELAY = 1_000;

/** Maximum reconnect delay in milliseconds. */
const MAX_RECONNECT_DELAY = 30_000;

/** Backoff multiplier; delay doubles each attempt. */
const RECONNECT_BACKOFF_MULTIPLIER = 2;

/** Jitter factor — ±10% of the calculated delay. */
const JITTER_FACTOR = 0.1;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Calculate the delay for a given reconnect attempt with exponential
 * backoff and jitter.
 */
function getBackoffDelay(attempt: number): number {
  const delay = INITIAL_RECONNECT_DELAY * RECONNECT_BACKOFF_MULTIPLIER ** attempt;
  const capped = Math.min(delay, MAX_RECONNECT_DELAY);
  const jitter = capped * (Math.random() * 2 - 1) * JITTER_FACTOR; // ±10%
  return Math.round(capped + jitter);
}

/** Build the WebSocket URL from the current window location. */
function getWebSocketUrl(): string {
  const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${scheme}//${window.location.host}/ws/dashboard`;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useWebSocket() {
  const queryClient = useQueryClient();
  const setHealth = useHealthStore((state) => state.setHealth);
  const [status, setStatus] = useState<WSStatus>('connecting');

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  /** Clean up any pending reconnect timer. */
  const clearReconnect = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  /** Disconnect the current WebSocket and clear timers. */
  const disconnect = useCallback(() => {
    clearReconnect();
    if (wsRef.current !== null) {
      const ws = wsRef.current;
      wsRef.current = null;

      // Remove listeners to prevent the onclose → reconnect logic from firing
      ws.onopen = null;
      ws.onclose = null;
      ws.onmessage = null;
      ws.onerror = null;

      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close(1000, 'Client disconnect');
      }
    }
  }, [clearReconnect]);

  /** Schedule a reconnect attempt with exponential backoff. */
  const scheduleReconnect = useCallback(() => {
    if (!isMountedRef.current) return;

    clearReconnect();
    const delay = getBackoffDelay(reconnectAttemptRef.current);

    reconnectTimerRef.current = setTimeout(() => {
      reconnectTimerRef.current = null;
      reconnectAttemptRef.current += 1;
      connectRef.current();
    }, delay);
  }, [clearReconnect]);

  /** Open a new WebSocket connection. */
  const connect = useCallback(() => {
    if (!isMountedRef.current) return;
    if (wsRef.current !== null) return; // Already connecting or connected

    setStatus('connecting');
    const url = getWebSocketUrl();
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!isMountedRef.current) {
        ws.close();
        return;
      }
      reconnectAttemptRef.current = 0;
      setStatus('connected');
    };

    ws.onclose = () => {
      if (!isMountedRef.current) return;
      wsRef.current = null;
      setStatus('disconnected');
      scheduleReconnect();
    };

    ws.onmessage = (event: MessageEvent<string>) => {
      if (!isMountedRef.current) return;
      try {
        const message = JSON.parse(event.data) as WSMessage<unknown>;
        handleMessage(message, queryClient, setHealth);
      } catch {
        // Silently ignore malformed messages
      }
    };

    ws.onerror = () => {
      // Errors are handled by onclose; no-op
    };
  }, [queryClient, setHealth, scheduleReconnect]);

  // Store connect in a ref so scheduleReconnect can access the latest version
  const connectRef = useRef(connect);
  connectRef.current = connect;

  // -------------------------------------------------------------------------
  // Effect: connect on mount, disconnect on unmount
  // -------------------------------------------------------------------------
  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [connect, disconnect]);

  return { status };
}

// ---------------------------------------------------------------------------
// Message dispatch
// ---------------------------------------------------------------------------

function handleMessage(
  message: WSMessage<unknown>,
  queryClient: ReturnType<typeof useQueryClient>,
  setHealth: (seatId: string, data: import('@/store/healthStore').HealthMetrics) => void,
): void {
  switch (message.type) {
    case 'seat_updated': {
      const payload = message.payload as SeatUpdatedPayload;
      const seatId = payload.id ?? payload.seat_id;

      // Invalidate the seat list so the grid refetches
      queryClient.invalidateQueries({ queryKey: ['seats'] });

      // If we have a specific seat ID, also invalidate its detail cache
      if (seatId) {
        queryClient.invalidateQueries({ queryKey: ['seat', seatId] });
      }
      break;
    }

    case 'health_update': {
      const payload = message.payload as HealthUpdatePayload;
      if (!payload.seat_id) break;

      setHealth(payload.seat_id, {
        seat_id: payload.seat_id,
        cpu_pct: payload.cpu_pct,
        ram_pct: payload.ram_pct,
        cpu_temp: payload.cpu_temp,
        disk_used_gb: payload.disk_used_gb,
        disk_total_gb: payload.disk_total_gb,
        timestamp: payload.timestamp,
      });
      break;
    }

    case 'announcement': {
      const payload = message.payload as AnnouncementPayload;
      console.info('Announcement:', payload.message);
      // Future: integrate speaker or toast notification
      break;
    }

    case 'alert': {
      const payload = message.payload as AlertPayload;
      console.warn('Alert:', payload.type, payload.message, payload.seat_id);
      // Future: display alert banner in UI
      break;
    }

    default:
      // Unknown event type — ignore
      break;
  }
}
