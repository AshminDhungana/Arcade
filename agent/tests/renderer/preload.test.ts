/**
 * @vitest-environment node
 */

import { describe, it, expect, vi } from 'vitest';

vi.mock('electron', () => ({
  contextBridge: {
    exposeInMainWorld: vi.fn(),
  },
  ipcRenderer: {
    on: vi.fn(),
    send: vi.fn(),
  },
}));

/* eslint-disable @typescript-eslint/no-explicit-any */

describe('preload API', () => {
  it('exposes all expected methods via contextBridge', async () => {
    const { contextBridge } = await import('electron');

    // Import has side-effect — calls exposeInMainWorld
    await import('../../src/renderer/preload.js');

    expect(contextBridge.exposeInMainWorld).toHaveBeenCalledWith(
      'electronAPI',
      expect.any(Object),
    );

    const exposedApi = (contextBridge.exposeInMainWorld as any).mock.calls[0][1];

    expect(exposedApi).toHaveProperty('onOverlayContent');
    expect(exposedApi).toHaveProperty('onTimerUpdate');
    expect(exposedApi).toHaveProperty('onAnnouncement');
    expect(exposedApi).toHaveProperty('onLowTimeWarning');
    expect(exposedApi).toHaveProperty('onSessionStatus');
    expect(exposedApi).toHaveProperty('callStaff');
    expect(exposedApi).toHaveProperty('staffOverride');
  });
});
