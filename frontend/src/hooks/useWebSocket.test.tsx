import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useWebSocket } from './useWebSocket';

// ---------------------------------------------------------------------------
// Mock WebSocket
// ---------------------------------------------------------------------------

type Listener = ((ev: Event) => void) | null;

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  url: string;
  onopen: Listener = null;
  onclose: Listener = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: Listener = null;
  readyState: number = WebSocket.CONNECTING;
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  triggerOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  triggerClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }

  triggerMessage(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  send() {
    // no-op in these tests
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.triggerClose();
  }

  static reset() {
    MockWebSocket.instances = [];
  }
}

// Replace the global WebSocket with our mock
vi.stubGlobal('WebSocket', MockWebSocket);

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

const createWrapper = (client: QueryClient) =>
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.reset();
  });

  afterEach(() => {
    MockWebSocket.reset();
    vi.useRealTimers();
  });

  it('initialises as connecting', () => {
    const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity } } });
    const { result } = renderHook(() => useWebSocket(), { wrapper: createWrapper(client) });

    expect(result.current.status).toBe('connecting');
  });

  it('transitions to connected after WebSocket opens', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity } } });
    const { result } = renderHook(() => useWebSocket(), { wrapper: createWrapper(client) });

    const lastInstance = MockWebSocket.instances[MockWebSocket.instances.length - 1];
    lastInstance.triggerOpen();

    // Wait for state to update
    await vi.waitFor(() => {
      expect(result.current.status).toBe('connected');
    });
  });

  it('transitions to disconnected on close', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity } } });
    const { result } = renderHook(() => useWebSocket(), { wrapper: createWrapper(client) });

    const lastInstance = MockWebSocket.instances[MockWebSocket.instances.length - 1];
    lastInstance.triggerOpen();
    await vi.waitFor(() => expect(result.current.status).toBe('connected'));

    lastInstance.triggerClose();
    await vi.waitFor(() => expect(result.current.status).toBe('disconnected'));
  });

  it('uses the correct WebSocket URL based on window.location', () => {
    const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity } } });
    renderHook(() => useWebSocket(), { wrapper: createWrapper(client) });

    const lastInstance = MockWebSocket.instances[MockWebSocket.instances.length - 1];
    expect(lastInstance.url).toBe('ws://localhost:3000/ws/dashboard');
  });
});
