// agent/src/renderer/hud-state.ts

export type HudPhase = 'INTRO' | 'AMBIENT' | 'URGENT' | 'ENDED';
export type HudEvent = 'session-start' | 'intro-timeout' | 'low-time' | 'session-end';

/** Pure HUD lifecycle reducer. The renderer holds `phase` and calls this on each
 *  real event; see spec §3. */
export function nextHudPhase(phase: HudPhase, event: HudEvent): HudPhase {
  switch (event) {
    case 'session-start':
      return 'INTRO';
    case 'intro-timeout':
      return phase === 'INTRO' ? 'AMBIENT' : phase;
    case 'low-time':
      return phase === 'INTRO' || phase === 'AMBIENT' ? 'URGENT' : phase;
    case 'session-end':
      return 'ENDED';
  }
}
