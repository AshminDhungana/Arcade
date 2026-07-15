// agent/src/renderer/setup.ts
// First-run setup renderer. Collects the enroll code and forwards it to the
// main process via the preload's `enroll` IPC.
//
// NOTE: The `electronAPI` global is declared once by the kiosk overlay's
// renderer (index.ts) with the shared surface (onOverlayContent, callStaff,
// staffOverride, …). Re-declaring `Window.electronAPI` here with a different
// inline type is a TS2717 error, so we narrow to just the `enroll` shape
// locally instead of re-declaring the global.
const codeEl = document.getElementById('code') as HTMLInputElement;
const statusEl = document.getElementById('status') as HTMLDivElement;

type EnrollFn = (code: string) => Promise<{ ok: boolean; error?: string }>;

document.getElementById('connect')?.addEventListener('click', async () => {
  const code = codeEl.value.trim().toUpperCase();
  if (!code) return;
  statusEl.textContent = 'Connecting…';
  const enroll = (window.electronAPI as unknown as { enroll: EnrollFn }).enroll;
  const res = await enroll(code);
  if (!res.ok) statusEl.textContent = res.error || 'Enrollment failed';
});

export {};
