// agent/src/renderer/motion.ts

/** Entrance reveal: fade + rise. No-op if Web Animations API is unavailable. */
export function reveal(el: HTMLElement, delayMs = 0): void {
  if (typeof el.animate !== 'function') return;
  el.animate(
    [{ opacity: 0, transform: 'translateY(12px)' }, { opacity: 1, transform: 'translateY(0)' }],
    { duration: 320, delay: delayMs, easing: 'cubic-bezier(.2,.7,.3,1)', fill: 'both' },
  );
}

/** Subtle per-second pulse on the timer digit group. */
export function pulseTimer(el: HTMLElement): void {
  if (typeof el.animate !== 'function') return;
  el.animate(
    [{ transform: 'scale(1)' }, { transform: 'scale(1.04)' }, { transform: 'scale(1)' }],
    { duration: 180, easing: 'ease-out' },
  );
}

/** Local countdown. Calls onTick immediately and every intervalMs; onDone at 0.
 *  Returns a stop function. */
export function countdown(
  fromSeconds: number,
  onTick: (remaining: number) => void,
  onDone?: () => void,
  intervalMs = 1000,
): () => void {
  let remaining = fromSeconds;
  onTick(remaining);
  const id = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearInterval(id);
      onTick(0);
      onDone?.();
      return;
    }
    onTick(remaining);
  }, intervalMs);
  return () => clearInterval(id);
}
