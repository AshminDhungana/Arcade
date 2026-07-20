// agent/tests/renderer/hud-state.test.ts
import { describe, it, expect } from 'vitest';
import { nextHudPhase, type HudPhase } from '../../src/renderer/hud-state.js';

describe('nextHudPhase', () => {
  it('session-start moves to INTRO from ENDED', () => {
    expect(nextHudPhase('ENDED', 'session-start')).toBe('INTRO');
  });
  it('intro-timeout moves INTRO to AMBIENT', () => {
    expect(nextHudPhase('INTRO', 'intro-timeout')).toBe('AMBIENT');
  });
  it('intro-timeout is a no-op outside INTRO', () => {
    expect(nextHudPhase('AMBIENT', 'intro-timeout')).toBe('AMBIENT');
  });
  it('low-time moves AMBIENT to URGENT', () => {
    expect(nextHudPhase('AMBIENT', 'low-time')).toBe('URGENT');
  });
  it('low-time moves INTRO to URGENT', () => {
    expect(nextHudPhase('INTRO', 'low-time')).toBe('URGENT');
  });
  it('session-end moves any phase to ENDED', () => {
    const phases: HudPhase[] = ['INTRO', 'AMBIENT', 'URGENT', 'ENDED'];
    for (const p of phases) expect(nextHudPhase(p, 'session-end')).toBe('ENDED');
  });
});
