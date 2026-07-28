# Code Splitting & Lazy Loading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement React.lazy + Suspense code splitting for all pages except Dashboard and Login, configure Vite manual chunks for recharts/react-query/zustand, target initial bundle < 500KB gzipped, add rollup-plugin-visualizer for bundle analysis.

**Architecture:** Frontend-only changes. Modify `App.tsx` to lazy-load route components, update `vite.config.ts` with manualChunks and visualizer plugin, add bundle analysis script to package.json. No backend or agent changes.

**Tech Stack:** React 19, Vite 8, react-router-dom 7, recharts 3, @tanstack/react-query 5, zustand 5, rollup-plugin-visualizer.

## Global Constraints

- Target: initial bundle < 500KB gzipped (per spec NFR-PERF-005)
- Lazy-load: Members, Analytics, Events, Settings pages only (Dashboard, Login eager)
- Manual chunks: `recharts`, `@tanstack/react-query`, `zustand` as separate vendor chunks
- Visualization: `rollup-plugin-visualizer` (not vite-bundle-analyzer, which is deprecated)
- Keep existing imports/exports intact — only wrap page components in `React.lazy()`
- Existing `Suspense` fallback pattern: reuse `<div className="flex h-64 items-center justify-center">Loading…</div>` style
- Run `npm run build` then `npx vite-bundle-analyzer` (or visualizer) to verify chunk sizes

---

### Task 1: Add rollup-plugin-visualizer to package.json

**Files:**
- Modify: `frontend/package.json`

**Interfaces:**
- Produces: devDependency `rollup-plugin-visualizer` available for vite config

- [ ] **Step 1: Write the failing test** — N/A (configuration change)

- [ ] **Step 2: Add dependency**

```bash
cd frontend && npm install -D rollup-plugin-visualizer
```

- [ ] **Step 3: Verify install**

```bash
cd frontend && npm ls rollup-plugin-visualizer
```
Expected: `rollup-plugin-visualizer@^5.x.x`

- [ ] **Step 4: Add analyze script to package.json**

In `frontend/package.json`, add to `"scripts"`:
```json
"analyze": "vite build --mode analyze"
```

- [ ] **Step 5: Commit**

```bash
cd frontend && git add package.json package-lock.json && git commit -m "feat: add rollup-plugin-visualizer for bundle analysis"
```

---

### Task 2: Configure Vite manualChunks and visualizer plugin

**Files:**
- Modify: `frontend/vite.config.ts`

**Interfaces:**
- Consumes: `rollup-plugin-visualizer` from Task 1
- Produces: `build.rollupOptions.output.manualChunks` config, `plugins` array includes visualizer in analyze mode

- [ ] **Step 1: Read current vite.config.ts**

```bash
cat frontend/vite.config.ts
```

- [ ] **Step 2: Write the failing test** — N/A (config change)

- [ ] **Step 3: Update vite.config.ts**

Replace the entire `vite.config.ts` with:

```ts
/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';
import { visualizer } from 'rollup-plugin-visualizer';

// FaviconIcon SVG string (inline to avoid importing broken lucide icons)
const FaviconIcon = `<svg
  xmlns="http://www.w3.org/2000/svg"
  width="32"
  height="32"
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="2"
  stroke-linecap="round"
  stroke-linejoin="round"
>
  <path d="M11.146 15.854a1.207 1.207 0 0 1 1.708 0l1.56 1.56A2 2 0 0 1 15 18.828V21a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1v-2.172a2 2 0 0 1 .586-1.414z" />
  <path d="M18.828 15a2 2 0 0 1-1.414-.586l-1.56-1.56a1.207 1.207 0 0 1 0-1.708l1.56-1.56A2 2 0 0 1 18.828 9H21a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1z" />
  <path d="M6.586 14.414A2 2 0 0 1 5.172 15H3a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h2.172a2 2 0 0 1 1.414.586l1.56 1.56a1.207 1.207 0 0 1 0 1.708z" />
  <path d="M9 3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2.172a2 2 0 0 1-.586 1.414l-1.56 1.56a1.207 1.207 0 0 1-1.708 0l-1.56-1.56A2 2 0 0 1 9 5.172z" />
</svg>`;

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const isAnalyze = mode === 'analyze';

  return {
    plugins: [
      react(),
      tailwindcss(),
      {
        name: 'inject-favicon',
        enforce: 'post',
        apply: 'build',
        transformIndexHtml(html: string) {
          const faviconDataUri = `data:image/svg+xml,${encodeURIComponent(FaviconIcon)}`;
          return html.replace(
            /<link rel="icon"[^>]*>/g,
            `<link rel="icon" type="image/svg+xml" href="${faviconDataUri}" />`
          );
        },
      },
      isAnalyze && visualizer({
        filename: 'dist/stats.html',
        open: true,
        gzipSize: true,
        brotliSize: true,
      }),
    ].filter(Boolean),
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      proxy: {
        '/api': 'http://localhost:8741',
        '/ws': { target: 'ws://localhost:8741', ws: true },
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-recharts': ['recharts'],
            'vendor-react-query': ['@tanstack/react-query'],
            'vendor-zustand': ['zustand'],
          },
        },
      },
    },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test-setup.ts'],
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    },
  };
});
```

- [ ] **Step 4: Verify config syntax**

```bash
cd frontend && npx vite build --mode analyze 2>&1 | head -50
```
Expected: Build starts, generates `dist/stats.html`, opens browser

- [ ] **Step 5: Commit**

```bash
cd frontend && git add vite.config.ts && git commit -m "feat: configure manualChunks for recharts, react-query, zustand + visualizer"
```

---

### Task 3: Convert page imports to React.lazy in App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: Page component exports from `./pages/*` (unchanged)
- Produces: Lazy-loaded route components wrapped in `<Suspense>`

- [ ] **Step 1: Read current App.tsx**

```bash
cat frontend/src/App.tsx
```

- [ ] **Step 2: Write failing test** — N/A (UI routing change; covered by existing e2e tests)

- [ ] **Step 3: Update App.tsx**

Replace the entire file with:

```tsx
import { useEffect, Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { RequireFeature } from './components/RequireFeature';
import { useFeatureFlags } from './api/featureFlags';
import { ToastViewport } from '@/components/ui/Toast';
import { NavShell } from './components/NavShell';
import { useThemeStore } from '@/store/themeStore';

// Eager-loaded pages (Dashboard, Login)
import Login from './pages/Login';
import DashboardPage from './pages/Dashboard';

// Lazy-loaded pages
const MembersPage = lazy(() => import('./pages/Members').then(m => ({ default: m.MembersPage })));
const AnalyticsPage = lazy(() => import('./pages/Analytics').then(m => ({ default: m.AnalyticsPage })));
const EventsPage = lazy(() => import('./pages/Events').then(m => ({ default: m.EventsPage })));
const SettingsPage = lazy(() => import('./pages/Settings').then(m => ({ default: m.default })));

// Suspense fallback
function PageFallback() {
  return (
    <div className="flex h-64 items-center justify-center" role="status" aria-label="Loading page">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-primary" />
    </div>
  );
}

export default function App() {
  // Bootstrap feature flags from GET /api/settings on mount
  useFeatureFlags();

  // Initialize theme (applies .dark class to <html> if needed)
  const initializeTheme = useThemeStore((s) => s.initialize);
  useEffect(() => {
    initializeTheme();
  }, [initializeTheme]);

  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <NavShell>
                <DashboardPage />
              </NavShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/members"
          element={
            <ProtectedRoute>
              <RequireFeature flag="enable_members">
                <NavShell>
                  <Suspense fallback={<PageFallback />}>
                    <MembersPage />
                  </Suspense>
                </NavShell>
              </RequireFeature>
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <ProtectedRoute>
              <NavShell>
                <Suspense fallback={<PageFallback />}>
                  <AnalyticsPage />
                </Suspense>
              </NavShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/events"
          element={
            <ProtectedRoute>
              <RequireFeature flag="enable_tournaments">
                <NavShell>
                  <Suspense fallback={<PageFallback />}>
                    <EventsPage />
                  </Suspense>
                </NavShell>
              </RequireFeature>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <NavShell>
                <Suspense fallback={<PageFallback />}>
                  <SettingsPage />
                </Suspense>
              </NavShell>
            </ProtectedRoute>
          }
        />
      </Routes>
      <ToastViewport />
    </>
  );
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && npx tsc -b
```
Expected: No errors

- [ ] **Step 5: Run dev server quick smoke test**

```bash
cd frontend && timeout 10 npm run dev 2>&1 | head -30
```
Expected: Vite starts, no module resolution errors

- [ ] **Step 6: Commit**

```bash
cd frontend && git add src/App.tsx && git commit -m "feat: lazy-load Members, Analytics, Events, Settings pages with Suspense"
```

---

### Task 4: Build and analyze bundle sizes

**Files:**
- None new (uses config from Task 2)

**Interfaces:**
- Consumes: Vite config with manualChunks + visualizer
- Produces: `frontend/dist/stats.html` with chunk size breakdown

- [ ] **Step 1: Run production build with analysis**

```bash
cd frontend && npm run build -- --mode analyze
```
Expected: Build completes, `dist/stats.html` generated, browser opens with visualizer

- [ ] **Step 2: Verify manual chunks created**

```bash
ls -la frontend/dist/assets/
```
Expected: Files like `vendor-recharts-[hash].js`, `vendor-react-query-[hash].js`, `vendor-zustand-[hash].js`, plus page chunks `MembersPage-[hash].js`, etc.

- [ ] **Step 3: Check gzipped sizes**

```bash
cd frontend/dist/assets && gzip -c *.js | wc -c
```
Or use the visualizer UI (stats.html) — note the "Gzip" column for each chunk.

- [ ] **Step 4: Verify initial bundle < 500KB gzipped**

In visualizer UI, check the "Initial" chunks total gzipped size. Main entry + vendor chunks (excluding lazy page chunks) should be < 500KB.

- [ ] **Step 5: If over budget, iterate**

Options (in order):
1. Move more vendor libs to manual chunks (e.g., `lucide-react`, `motion`, `@radix-ui/*`)
2. Ensure `recharts` chunk is not pulled into entry (check visualizer graph)
3. Consider `build.minify: 'terser'` with `compress: { drop_console: true }`

- [ ] **Step 6: Commit verified build**

```bash
cd frontend && git add dist/ && git commit -m "chore: verified bundle split — initial < 500KB gzipped"
```
(Note: `dist/` is normally gitignored; this commit is for verification record only. In practice, CI verifies on every PR.)

---

### Task 5: Run existing tests to ensure no regressions

**Files:**
- Test: `frontend/src/**/*.test.tsx`, `frontend/e2e/**/*.spec.ts`

**Interfaces:**
- Consumes: Modified `App.tsx` routing
- Produces: Passing test suite

- [ ] **Step 1: Run unit tests**

```bash
cd frontend && npm run test
```
Expected: All vitest tests pass

- [ ] **Step 2: Run e2e tests (if Playwright configured)**

```bash
cd frontend && npm run test:e2e
```
Expected: All Playwright tests pass (navigation, lazy load, Suspense fallback)

- [ ] **Step 3: Fix any failures**

If lazy loading breaks a test (e.g., missing `await waitFor` for Suspense), update the test to handle async rendering.

- [ ] **Step 4: Commit**

```bash
cd frontend && git add -A && git commit -m "test: verify lazy loading works with existing test suite"
```

---

### Task 6: Update TODO.md to mark task complete

**Files:**
- Modify: `docs/TODO.md`

**Interfaces:**
- Consumes: Completed implementation
- Produces: Updated task checkbox

- [ ] **Step 1: Read TODO.md lines 1743-1747**

```bash
sed -n '1743,1747p' docs/TODO.md
```

- [ ] **Step 2: Update checkboxes to `[x]`**

Edit `docs/TODO.md` lines 1743-1747:
```markdown
- [x] **Task: Code splitting and lazy loading**
  - [x] `React.lazy()` + `Suspense` for all pages except `Dashboard` and `Login`
  - [x] Vite `rollupOptions.manualChunks`: separate chunks for recharts, react-query, zustand
  - [x] Target: initial bundle < 500KB gzipped
  - [x] Use `rollup-plugin-visualizer` to inspect chunk sizes
```

- [ ] **Step 3: Commit**

```bash
git add docs/TODO.md && git commit -m "chore: mark Phase 10 Epic 10.2 code splitting task complete"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] React.lazy + Suspense for Members, Analytics, Events, Settings — Task 3
- [x] Dashboard, Login eager-loaded — Task 3
- [x] Manual chunks for recharts, react-query, zustand — Task 2
- [x] Target < 500KB gzipped initial — Task 4
- [x] rollup-plugin-visualizer for inspection — Task 1, 2, 4

**Placeholders:** None — all code blocks complete, exact commands provided.

**Type consistency:** `lazy(() => import(...).then(m => ({ default: m.MembersPage })))` matches named export pattern in `Members.tsx` (exports `MembersPage`), `Analytics.tsx` (exports `AnalyticsPage`), `Events.tsx` (exports `EventsPage`), `Settings.tsx` (default export).

---

**Plan complete and saved to `docs/superpowers/plans/2026-07-28-code-splitting-lazy-loading-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
