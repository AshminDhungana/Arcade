import '@testing-library/jest-dom/vitest';

// jsdom does not implement ResizeObserver; Radix primitives (Switch, etc.) use it.
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserver as unknown as typeof ResizeObserver;

// jsdom does not implement matchMedia; Motion's useReducedMotion needs it.
// Default: no reduced-motion preference (animations on), matching real default.
// Tests can opt into reduced motion via setPrefersReducedMotion(true).
let prefersReducedMotion = false;

export function setPrefersReducedMotion(value: boolean): void {
  prefersReducedMotion = value;
}

if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: query.includes('prefers-reduced-motion')
        ? prefersReducedMotion
        : false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}
