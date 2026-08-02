/**
 * Secure IPC preload script for the kiosk overlay renderer.
 *
 * This script runs in the preload context (before the renderer) and exposes
 * a controlled API on `window.electronAPI` that the renderer can use to
 * communicate with the main process.  No Node.js APIs are exposed to the
 * renderer directly.
 *
 * Uses CommonJS require for Electron sandbox compatibility.
 */

const { contextBridge, ipcRenderer } = require('electron');

// ---------------------------------------------------------------------------
// Expose the controlled API to the renderer
// ---------------------------------------------------------------------------

const api = {
  onOverlayContent: (callback: (data: any) => void) => {
    ipcRenderer.on('overlay:update', (_event: any, data: any) => callback(data));
  },

  onTimerUpdate: (callback: (data: any) => void) => {
    ipcRenderer.on('overlay:timer', (_event: any, data: any) => callback(data));
  },

  onAnnouncement: (callback: (text: string, durationMs: number) => void) => {
    ipcRenderer.on('overlay:announcement', (_event: any, data: any) =>
      callback(data.text, data.durationMs),
    );
  },

  onLowTimeWarning: (callback: (minutes: number) => void) => {
    ipcRenderer.on('overlay:low-time', (_event: any, data: any) =>
      callback(data.minutes),
    );
  },

  onSessionStatus: (callback: (active: boolean) => void) => {
    ipcRenderer.on('overlay:session-active', (_event: any, data: any) =>
      callback(data.active),
    );
  },

  onConfig: (callback: (data: any) => void) => {
    ipcRenderer.on('agent:config', (_event: any, data: any) => callback(data));
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
