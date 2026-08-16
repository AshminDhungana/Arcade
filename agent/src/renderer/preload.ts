/**
 * Secure IPC preload script for the kiosk overlay renderer.
 *
 * This script runs in the preload context (before the renderer) and exposes
 * a controlled API on `window.electronAPI` that the renderer can use to
 * communicate with the main process.  No Node.js APIs are exposed to the
 * renderer directly.
 */

import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron';
import type { OverlayData } from './types.js';

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
  callStaffEnabled?: boolean;
  announcements?: string[];
  lowTimeWarning?: boolean;
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
    ipcRenderer.on('overlay:update', (_event: IpcRendererEvent, data: OverlayUpdateData) => {
      const fullData: OverlayData = {
        cafeName: data.cafeName ?? '',
        cafeLogo: data.cafeLogo,
        eventBanner: data.eventBanner,
        sessionActive: data.sessionActive ?? false,
        remainingTime: data.remainingTime?.toString(),
        overrideCodeConfigured: data.overrideCodeConfigured ?? false,
        serverUrl: data.serverUrl,
        seatId: data.seatId,
        agentSecret: data.agentSecret,
        callStaffEnabled: true,
        announcements: [],
        lowTimeWarning: false,
      };
      callback(fullData);
    });
  },

  onTimerUpdate: (callback: (data: TimerUpdateData) => void) => {
    ipcRenderer.on('overlay:timer', (_event: IpcRendererEvent, data: TimerUpdateData) => callback(data));
  },

  onAnnouncement: (callback: (text: string, durationMs: number) => void) => {
    ipcRenderer.on('overlay:announcement', (_event: IpcRendererEvent, data: AnnouncementData) =>
      callback(data.text, data.durationMs),
    );
  },

  onLowTimeWarning: (callback: (minutes: number) => void) => {
    ipcRenderer.on('overlay:low-time', (_event: IpcRendererEvent, data: LowTimeData) =>
      callback(data.minutes),
    );
  },

  onSessionStatus: (callback: (active: boolean) => void) => {
    ipcRenderer.on('overlay:session-active', (_event: IpcRendererEvent, data: SessionActiveData) =>
      callback(data.active),
    );
  },

  onConfig: (callback: (data: ConfigData) => void) => {
    ipcRenderer.on('agent:config', (_event: IpcRendererEvent, data: ConfigData) => callback(data));
  },

  callStaff: () => {
    ipcRenderer.send('call-staff');
  },

  staffOverride: (pin: string) =>
    ipcRenderer.invoke('staff-override', pin),

  verifySettingsPin: (pin: string) =>
    ipcRenderer.invoke('verify-settings-pin', pin),

  openSettings: () => ipcRenderer.send('agent:open-settings'),

  onStaffAlertAck: (callback: () => void) => {
    ipcRenderer.on('staff-alert-ack', (_event: IpcRendererEvent) => callback());
  },

  onSetMinimal: (callback: (enabled: boolean) => void) => {
    ipcRenderer.on('overlay:set-minimal', (_event: IpcRendererEvent, enabled: boolean) => callback(enabled));
  },

  onHotspot: (callback: (active: boolean) => void) => {
    ipcRenderer.on('overlay:hotspot', (_event: IpcRendererEvent, active: boolean) => callback(active));
  },

  onSuspend: (callback: () => void) => {
    ipcRenderer.on('overlay:suspend', (_event: IpcRendererEvent) => callback());
  },

  onResume: (callback: () => void) => {
    ipcRenderer.on('overlay:resume', (_event: IpcRendererEvent) => callback());
  },

  onRequestSync: (callback: () => void) => {
    ipcRenderer.on('overlay:request-sync', (_event: IpcRendererEvent) => callback());
  },

  setClickThrough: (clickThrough: boolean) => {
    ipcRenderer.send('overlay:click-through', clickThrough);
  },

  enroll: (code: string) =>
    ipcRenderer.invoke('agent:enroll', code),
};

contextBridge.exposeInMainWorld('electronAPI', api);
