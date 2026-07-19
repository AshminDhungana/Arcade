import '@testing-library/jest-dom/vitest';

// jsdom does not implement ResizeObserver; Radix primitives (Switch, etc.) use it.
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserver as unknown as typeof ResizeObserver;
