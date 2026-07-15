import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

export function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

/**
 * jsdom has no layout engine, so Recharts' ResponsiveContainer reports 0×0 and
 * renders nothing. Stub ResizeObserver to immediately report a fixed size and
 * override getBoundingClientRect so charts render in tests.
 */
export function installChartLayoutMocks(): void {
  (globalThis as { ResizeObserver?: unknown }).ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
  HTMLElement.prototype.getBoundingClientRect = () =>
    ({
      width: 800,
      height: 280,
      top: 0,
      left: 0,
      right: 800,
      bottom: 280,
      x: 0,
      y: 0,
      toJSON() {},
    }) as DOMRect;
}
