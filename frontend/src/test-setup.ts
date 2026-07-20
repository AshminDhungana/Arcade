import '@testing-library/jest-dom/vitest';

// jsdom does not implement ResizeObserver; Radix primitives (Switch, etc.) use it.
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserver as unknown as typeof ResizeObserver;

// jsdom does not implement matchMedia; Motion's useReducedMotion needs it.
if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}
