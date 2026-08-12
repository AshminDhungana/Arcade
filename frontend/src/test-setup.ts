import '@testing-library/jest-dom/vitest';

// jsdom does not implement ResizeObserver; Radix primitives (Switch, etc.) use it.
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserver as unknown as typeof ResizeObserver;

// Node >=22 exposes an experimental global `localStorage` that is a broken
// stub unless --localstorage-file is passed, which shadows jsdom's own
// implementation (vitest-dev/vitest#10867). Provide a real in-memory Storage
// when the environment lacks one.
if (typeof window !== 'undefined' && !window.localStorage) {
  const data = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (key) => (data.has(key) ? data.get(key)! : null),
    key: (index) => [...data.keys()][index] ?? null,
    removeItem: (key) => void data.delete(key),
    setItem: (key, value) => void data.set(key, String(value)),
  };
  Object.defineProperty(window, 'localStorage', {
    value: storage,
    configurable: true,
    writable: true,
  });
}

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
