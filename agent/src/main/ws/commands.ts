/**
 * Command handlers -- map server WebSocket commands to `IPlatformService` operations.
 *
 * Each handler receives the command payload and delegates to the platform service.
 * This keeps the WebSocket client decoupled from platform specifics.
 */

import type { IPlatformService } from '../platform/types.js';
import type { ServerCommandPayloads } from './types.js';
import type { SessionStore } from '../storage/types.js';

/** Map of server command names to handler functions. */
export type CommandHandlers = {
  [K in keyof ServerCommandPayloads]: (payload: ServerCommandPayloads[K]) => void | Promise<void>;
};

/** Dependencies required by the command handler factory. */
export interface HandlerDeps {
  seatId: string;
}

/**
 * Create a map of command handlers bound to a platform service.
 *
 * @param platform - The OS-specific platform service (from Feature 2.2.1)
 * @param deps - Handler dependencies (seat ID, etc.)
 * @returns A map of command handlers
 */
export function createCommandHandlers(
  platform: IPlatformService,
  _deps: HandlerDeps,
  store?: SessionStore,
): CommandHandlers {
  return {
    HIDE_OVERLAY(payload) {
      // Persist session locally so elapsed time survives disconnect/crash
      store?.persistSession(payload.session_id, _deps.seatId, payload.started_at);
      // Hide the kiosk overlay so the user can access the desktop
      platform.hideKioskOverlay();
    },

    SHOW_OVERLAY(payload) {
      // Clear local cache when session ends
      store?.clearSession(payload.session_id);
      // Show the kiosk overlay to block desktop access
      platform.showKioskOverlay({
        cafeName: 'Arcade', announcements: [], callStaffEnabled: true, sessionActive: false,
      });
    },

    SHOW_MESSAGE(payload) {
      // Display an announcement on the kiosk overlay
      const durationMs = (payload.duration_seconds ?? 5) * 1000;
      platform.sendAnnouncement(payload.text, durationMs);
    },

    async RESTART(_payload) {
      await platform.restartPC();
    },

    async SHUTDOWN(_payload) {
      await platform.shutdownPC();
    },

    async TAKE_SCREENSHOT(_payload) {
      // Screenshot is handled by the WebSocket client directly
      // (it needs to send the result back to the server via SCREENSHOT_RESULT message)
    },

    LOW_TIME_WARNING(_payload) {
      const { minutes_remaining } = _payload;
      // Show an announcement banner (legacy text toast)
      platform.sendAnnouncement(
        `Warning: ${minutes_remaining} minutes remaining`, 10_000,
      );
      // Also trigger the special low-time modal in the renderer
      if ('kioskWindow' in platform) {
        const kWin = (platform as unknown as { kioskWindow?: { webContents: { send: (channel: string, data: unknown) => void } } }).kioskWindow;
        if (kWin?.webContents) {
          kWin.webContents.send('overlay:low-time', { minutes: minutes_remaining });
        }
      }
    },

    RESET_OVERRIDE(_payload) {
      // Clears the staff override flag
      // Handled by the WebSocket client state machine
    },
  };
}
