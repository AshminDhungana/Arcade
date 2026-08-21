import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useHealthStore } from '@/store/healthStore';
import { useAlertStore } from '@/store/alertStore';
import type {
  WSMessage,
  WSStatus,
  SeatUpdatedPayload,
  HealthUpdatePayload,
  AnnouncementPayload,
  AlertPayload,
} from '@/types/ws';
import type { Seat, SeatStatus } from '@/types/seat';

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

type SubscriptionCallback = () => void;
type SubscriptionsMap = Map<string, Set<SubscriptionCallback>>;

export function useWebSocket() {
  const queryClient = useQueryClient();
  const setHealth = useHealthStore((state) => state.setHealth);
  const [status, setStatus] = useState<WSStatus>('connecting');

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);
  const subscriptionsRef = useRef<SubscriptionsMap>(new Map());

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
        handleMessage(message, queryClient, setHealth, subscriptionsRef.current);
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

  /** Subscribe to an event type (WebSocket or custom). Returns an unsubscribe function. */
  const subscribe = useCallback((
    eventType: string,
    callback: SubscriptionCallback
  ): (() => void) => {
    const subs = subscriptionsRef.current;
    if (!subs.has(eventType)) {
      subs.set(eventType, new Set());
    }
    subs.get(eventType)!.add(callback);

    return () => {
      const callbacks = subs.get(eventType);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          subs.delete(eventType);
        }
      }
    };
  }, []);

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

  return { status, subscribe };
}

// ---------------------------------------------------------------------------
// Message dispatch
// ---------------------------------------------------------------------------

function handleMessage(
  message: WSMessage<unknown>,
  queryClient: ReturnType<typeof useQueryClient>,
  setHealth: (seatId: string, data: import('@/store/healthStore').HealthMetrics) => void,
  subscriptions: SubscriptionsMap,
): void {
  // Trigger subscriptions for this event type
  const callbacks = subscriptions.get(message.type);
  if (callbacks) {
    callbacks.forEach((cb) => cb());
  }

  switch (message.type) {
    case 'seat_updated': {
      const payload = message.payload as SeatUpdatedPayload;
      const seatId = payload.id ?? payload.seat_id;

      // Optimistically update the single-seat cache for immediate UI feedback
      if (seatId) {
        queryClient.setQueryData<Seat>(['seat', seatId], (old: Seat | undefined) => {
          if (!old) return old;
          return {
            ...old,
            ...payload,
            id: seatId,
            status: (payload.status as SeatStatus) ?? old.status,
          } as Seat;
        });
      }

      // Also update the seat list cache if the payload has enough info
      queryClient.setQueryData<Seat[]>(['seats'], (old: Seat[] | undefined) => {
        if (!old || !seatId) return old;
        return old.map((seat) =>
          seat.id === seatId
            ? ({
                ...seat,
                ...payload,
                id: seatId,
                status: (payload.status as SeatStatus) ?? seat.status,
              } as Seat)
            : seat
        );
      });

      // Invalidate to trigger background refetch for consistency
      queryClient.invalidateQueries({ queryKey: ['seats'] });
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
      if (!payload.seat_id) break;
      useAlertStore.getState().push({
        type: payload.type,
        seat_id: payload.seat_id,
        message: payload.message,
        timestamp: message.timestamp,
      });
      break;
    }

    default:
      // Unknown event type — ignore
      break;
  }
}
