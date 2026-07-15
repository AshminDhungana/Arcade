/**
 * Secure IPC preload script for the kiosk overlay renderer.
 *
 * This script runs in the preload context (before the renderer) and exposes
 * a controlled API on `window.electronAPI` that the renderer can use to
 * communicate with the main process.  No Node.js APIs are exposed to the
 * renderer directly.
 */

import { contextBridge, ipcRenderer } from 'electron';

/** Shape of overlay data sent from main → renderer. */
export interface OverlayData {
  cafeName: string;
  cafeLogo?: string;
  sessionActive: boolean;
  remainingTime?: string;
  lowTimeWarning?: boolean;
  callStaffEnabled: boolean;
  announcements: string[];
}

/** The API exposed to the renderer process via `window.electronAPI`. */
interface ElectronAPI {
  /** Main → Renderer: update the entire overlay content. */
  onOverlayContent: (callback: (data: OverlayData) => void) => void;

  /** Main → Renderer: update the visible timer string. */
  onTimerUpdate: (callback: (timeString: string) => void) => void;

  /** Main → Renderer: show an announcement toast/banner. */
  onAnnouncement: (callback: (text: string, durationMs: number) => void) => void;

  /** Main → Renderer: show the low-time warning modal. */
  onLowTimeWarning: (callback: (minutes: number) => void) => void;

  /** Main → Renderer: update whether a session is currently active. */
  onSessionStatus: (callback: (active: boolean) => void) => void;

  /** Renderer → Main: request staff attention. */
  callStaff: () => void;

  /** Renderer → Main: attempt a staff override with the given PIN. */
  staffOverride: (pin: string) => void;

  /** Renderer → Main: open the agent settings (setup) window. */
  openSettings: () => void;

  /** Renderer → Main: enroll this agent using the given code. */
  enroll: (code: string) => Promise<{ ok: boolean; error?: string }>;
}

// ---------------------------------------------------------------------------
// Expose the controlled API to the renderer
// ---------------------------------------------------------------------------

const api: ElectronAPI = {
  onOverlayContent: (callback) => {
    ipcRenderer.on('overlay:update', (_event, data) => callback(data));
  },

  onTimerUpdate: (callback) => {
    ipcRenderer.on('overlay:timer', (_event, data) => callback(data.timeString));
  },

  onAnnouncement: (callback) => {
    ipcRenderer.on('overlay:announcement', (_event, data) =>
      callback(data.text, data.durationMs),
    );
  },

  onLowTimeWarning: (callback) => {
    ipcRenderer.on('overlay:low-time', (_event, data) =>
      callback(data.minutes),
    );
  },

  onSessionStatus: (callback) => {
    ipcRenderer.on('overlay:session-active', (_event, data) =>
      callback(data.active),
    );
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
