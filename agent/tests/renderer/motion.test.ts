// agent/tests/renderer/motion.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { countdown, reveal, pulseTimer } from '../../src/renderer/motion.js';

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

describe('reduced-motion guard', () => {
  const orig = globalThis.matchMedia;
  afterEach(() => { globalThis.matchMedia = orig; });
  function stub(matches: boolean) {
    // minimal MediaQueryList stub; only `.matches` is read
    globalThis.matchMedia = ((query: string) => ({ matches, media: query })) as unknown as typeof matchMedia;
  }
  function elWithAnimate() {
    const el = document.createElement('div');
    const animate = vi.fn();
    (el as unknown as { animate: unknown }).animate = animate;
    return { el, animate };
  }

  it('reveal no-ops under reduced motion', () => {
    stub(true);
    const { el, animate } = elWithAnimate();
    reveal(el);
    expect(animate).not.toHaveBeenCalled();
  });

  it('reveal animates when reduced motion is not preferred', () => {
    stub(false);
    const { el, animate } = elWithAnimate();
    reveal(el);
    expect(animate).toHaveBeenCalledOnce();
  });

  it('pulseTimer no-ops under reduced motion', () => {
    stub(true);
    const { el, animate } = elWithAnimate();
    pulseTimer(el);
    expect(animate).not.toHaveBeenCalled();
  });
});
