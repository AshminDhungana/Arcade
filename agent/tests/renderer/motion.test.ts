// agent/tests/renderer/motion.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { countdown } from '../../src/renderer/motion.js';

describe('countdown', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('calls onTick immediately then each second, ending at 0', () => {
    const ticks: number[] = [];
    countdown(2, (r) => ticks.push(r));
    expect(ticks).toEqual([2]);
    vi.advanceTimersByTime(1000);
    expect(ticks).toEqual([2, 1]);
    vi.advanceTimersByTime(1000);
    expect(ticks).toEqual([2, 1, 0]);
  });

  it('calls onDone at zero', () => {
    const done = vi.fn();
    countdown(1, () => {}, done);
    vi.advanceTimersByTime(1000);
    expect(done).toHaveBeenCalledOnce();
  });

  it('returns a stop function that halts ticks', () => {
    const ticks: number[] = [];
    const stop = countdown(5, (r) => ticks.push(r));
    vi.advanceTimersByTime(1000);
    stop();
    vi.advanceTimersByTime(5000);
    expect(ticks).toEqual([5, 4]);
  });
});
