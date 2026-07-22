// frontend/src/store/themeStore.test.ts
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { useThemeStore } from './themeStore';

const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};

describe('themeStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('localStorage', mockLocalStorage);
    vi.stubGlobal('document', {
      documentElement: { classList: { add: vi.fn(), remove: vi.fn(), toggle: vi.fn(), contains: vi.fn() } },
    });
    useThemeStore.setState({ theme: 'dark' }); // reset store
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('can set theme to dark', () => {
    useThemeStore.getState().setTheme('dark');
    expect(useThemeStore.getState().theme).toBe('dark');
  });

  it('can set theme to light', () => {
    useThemeStore.getState().setTheme('light');
    expect(useThemeStore.getState().theme).toBe('light');
  });

  it('toggles theme from dark to light', () => {
    useThemeStore.getState().setTheme('dark');
    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().theme).toBe('light');
  });

  it('toggles theme from light to dark', () => {
    useThemeStore.getState().setTheme('light');
    useThemeStore.getState().toggleTheme();
    expect(useThemeStore.getState().theme).toBe('dark');
  });

  it('initialize applies dark theme to document class', () => {
    useThemeStore.getState().setTheme('dark');
    useThemeStore.getState().initialize();
    expect(document.documentElement.classList.toggle).toHaveBeenCalledWith('dark', true);
  });

  it('initialize applies light theme to document class', () => {
    useThemeStore.getState().setTheme('light');
    useThemeStore.getState().initialize();
    expect(document.documentElement.classList.toggle).toHaveBeenCalledWith('dark', false);
  });
});
