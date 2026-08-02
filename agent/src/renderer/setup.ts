// agent/src/renderer/setup.ts
// First-run setup renderer. Collects the enroll code and forwards it to the
// main process via the preload's `enroll` IPC.
const codeEl = document.getElementById('code') as HTMLInputElement;
const statusEl = document.getElementById('status') as HTMLDivElement;

type EnrollFn = (code: string) => Promise<{ ok: boolean; error?: string }>;

document.getElementById('connect')?.addEventListener('click', async () => {
  const code = codeEl.value.trim().toUpperCase();
  if (!code) return;
  console.log('[setup] Connect clicked, code:', code);
  statusEl.textContent = 'Connecting…';
  const enroll = (window.electronAPI as unknown as { enroll: EnrollFn }).enroll;
  console.log('[setup] Calling enroll...');
  const res = await enroll(code);
  console.log('[setup] Enroll result:', res);
  if (!res.ok) statusEl.textContent = res.error || 'Enrollment failed';
});

export {};
