let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  if (audioCtx) return audioCtx;
  try {
    audioCtx = new AudioContext();
  } catch {
    audioCtx = null;
  }
  return audioCtx;
}

/** Play a short two-tone "staff alert" ding. Never throws. */
export function playStaffAlertChime(): void {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    void ctx.resume();

    const now = ctx.currentTime;
    [660, 880].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq;
      const start = now + i * 0.15;
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.2, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.2);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.25);
    });
  } catch {
    // Audio failure must never break alert delivery
  }
}
