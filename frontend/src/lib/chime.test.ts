import { describe, it, expect, vi, beforeEach } from 'vitest';

class FakeOscillator {
  type = '';
  frequency = { value: 0 };
  connect = vi.fn();
  start = vi.fn();
  stop = vi.fn();
}

class FakeGain {
  gain = { setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() };
  connect = vi.fn();
}

class FakeAudioContext {
  static instances: FakeAudioContext[] = [];
  currentTime = 0;
  destination = {};
  resume = vi.fn();
  createOscillator = vi.fn(() => new FakeOscillator());
  createGain = vi.fn(() => new FakeGain());

  constructor() {
    FakeAudioContext.instances.push(this);
  }
}

describe('playStaffAlertChime', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('plays a two-tone ding through a Web Audio context', async () => {
    FakeAudioContext.instances = [];
    vi.stubGlobal('AudioContext', FakeAudioContext);

    const { playStaffAlertChime: play } = await import('./chime');
    play();

    const ctx = FakeAudioContext.instances[0];
    expect(ctx.createOscillator).toHaveBeenCalledTimes(2);
    expect(ctx.resume).toHaveBeenCalled();
  });

  it('silently does nothing when AudioContext is unavailable', async () => {
    vi.stubGlobal('AudioContext', undefined);

    const { playStaffAlertChime: play } = await import('./chime');
    expect(() => play()).not.toThrow();
  });
});
