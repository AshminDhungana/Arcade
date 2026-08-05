/** Shared renderer type definitions. */

export interface OverlayData {
  cafeName: string;
  cafeLogo?: string;
  sessionActive: boolean;
  remainingTime?: string;
  lowTimeWarning?: boolean;
  callStaffEnabled: boolean;
  announcements: string[];
  eventBanner?: string;
  overrideCodeConfigured: boolean;
  serverUrl?: string;
  seatId?: string;
  agentSecret?: string;
}

export interface ElectronAPI {
  onOverlayContent: (callback: (data: OverlayData) => void) => void;
  onTimerUpdate: (callback: (timer: { elapsedSeconds: number }) => void) => void;
  onAnnouncement: (callback: (text: string, durationMs: number) => void) => void;
  onLowTimeWarning: (callback: (minutes: number) => void) => void;
  onSessionStatus: (callback: (active: boolean) => void) => void;
  onConfig: (callback: (config: { hasOverrideCode: boolean }) => void) => void;
  callStaff: () => void;
  staffOverride: (pin: string) => void;
  openSettings: () => void;
  enroll: (code: string) => Promise<{ ok: boolean; error?: string }>;
  onStaffAlertAck: (callback: () => void) => void;
  verifySettingsPin: (pin: string) => Promise<boolean>;
  onSetMinimal: (callback: (enabled: boolean) => void) => void;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}
