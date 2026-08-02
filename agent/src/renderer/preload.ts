/**
 * Secure IPC preload script for the kiosk overlay renderer.
 *
 * This script runs in the preload context (before the renderer) and exposes
 * a controlled API on `window.electronAPI` that the renderer can use to
 * communicate with the main process.  No Node.js APIs are exposed to the
 * renderer directly.
 */

import { contextBridge, ipcRenderer } from 'electron';
import type { OverlayData } from './types.js';

interface IpcEvent extends Event {
  sender: unknown;
}

interface OverlayUpdateData {
  cafeName?: string;
  cafeLogo?: string;
  eventBanner?: string;
  sessionActive?: boolean;
  remainingTime?: number;
  overrideCodeConfigured?: boolean;
  serverUrl?: string;
  seatId?: string;
  agentSecret?: string;
}

interface TimerUpdateData {
  elapsedSeconds: number;
}

interface AnnouncementData {
  text: string;
  durationMs: number;
}

interface LowTimeData {
  minutes: number;
}

interface SessionActiveData {
  active: boolean;
}

interface ConfigData {
  hasOverrideCode: boolean;
}

// ---------------------------------------------------------------------------
// Expose the controlled API to the renderer
// ---------------------------------------------------------------------------

const api = {
  onOverlayContent: (callback: (data: OverlayData) => void) => {
    ipcRenderer.on('overlay:update', (_event: IpcEvent, data: OverlayUpdateData) => callback(data));
  },

  onTimerUpdate: (callback: (data: TimerUpdateData) => void) => {
    ipcRenderer.on('overlay:timer', (_event: IpcEvent, data: TimerUpdateData) => callback(data));
  },

  onAnnouncement: (callback: (text: string, durationMs: number) => void) => {
    ipcRenderer.on('overlay:announcement', (_event: IpcEvent, data: AnnouncementData) =>
      callback(data.text, data.durationMs),
    );
  },

  onLowTimeWarning: (callback: (minutes: number) => void) => {
    ipcRenderer.on('overlay:low-time', (_event: IpcEvent, data: LowTimeData) =>
      callback(data.minutes),
    );
  },

  onSessionStatus: (callback: (active: boolean) => void) => {
    ipcRenderer.on('overlay:session-active', (_event: IpcEvent, data: SessionActiveData) =>
      callback(data.active),
    );
  },

  onConfig: (callback: (data: ConfigData) => void) => {
    ipcRenderer.on('agent:config', (_event: IpcEvent, data: ConfigData) => callback(data));
  },

  callStaff: () => {
    ipcRenderer.send('call-staff');
  },

  staffOverride: (pin: string) => {
    ipcRenderer.send('staff-override', pin);
  },

  openSettings: () => ipcRenderer.send('agent:open-settings'),

  enroll: (code: string) =>
    ipcRenderer.invoke('agent:enroll', code),
};

contextBridge.exposeInMainWorld('electronAPI', api);
