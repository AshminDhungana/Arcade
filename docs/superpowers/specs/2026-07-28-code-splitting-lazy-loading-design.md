# Code Splitting & Lazy Loading Design

**Date:** 2026-07-28
**Status:** Approved
**Phase:** 10 (Performance Optimisation) — Epic 10.2 Frontend Performance

---

## 1. Objective

Reduce the initial JavaScript bundle to **< 500 KB gzipped** by:
- Lazy-loading all pages except `Dashboard` and `Login`
- Creating explicit vendor chunks for `recharts`, `@tanstack/react-query`, and `zustand`
- Enabling auto-splitting for remaining `node_modules`
- Adding `vite-bundle-analyzer` for ongoing bundle inspection

---

## 2. Current State

- `frontend/src/App.tsx` imports all 7 pages eagerly (lines 3–9)
- `vite.config.ts` has no `rollupOptions.manualChunks`
- No bundle analyzer configured
- Single combined bundle on initial load

---

## 3. Changes

### 3.1 `frontend/package.json`
Add devDependency:
```json
"vite-bundle-analyzer": "^0.12.0"
```

### 3.2 `frontend/vite.config.ts`
Add plugin import and configure:
```typescript
import { visualizer } from 'vite-bundle-analyzer';

// In plugins array:
visualizer({
  filename: 'dist/stats.html',
  open: false,
  gzipSize: true,
  brotliSize: true,
}),

// In build config:
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
```

### 3.3 New: `frontend/src/components/ui/PageLoader.tsx`
```tsx
export function PageLoader() {
  return (
    <div className="flex h-64 items-center justify-center text-muted-foreground" role="status" aria-label="Loading page">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-primary" />
      <span className="ml-3">Loading…</span>
    </div>
  );
}
```

### 3.4 `frontend/src/App.tsx`
Replace eager imports with `React.lazy()` for 4 pages:
```tsx
import { Suspense, lazy } from 'react';

const DashboardPage = () => import('./pages/Dashboard'); // eager
const Login = () => import('./pages/Login');             // eager

const MembersPage = lazy(() => import('./pages/Members'));
const AnalyticsPage = lazy(() => import('./pages/Analytics'));
const EventsPage = lazy(() => import('./pages/Events'));
const SettingsPage = lazy(() => import('./pages/Settings'));

import { PageLoader } from '@/components/ui/PageLoader';

// In routes, wrap lazy pages:
<Route
  path="/members"
  element={
    <ProtectedRoute>
      <RequireFeature flag="enable_members">
        <NavShell>
          <Suspense fallback={<PageLoader />}>
            <MembersPage />
          </Suspense>
        </NavShell>
      </RequireFeature>
    </ProtectedRoute>
  }
/>
// Repeat pattern for /analytics, /events, /settings
```

---

## 4. Chunk Strategy (Hybrid)

| Chunk Name | Contents | Rationale |
|------------|----------|-----------|
| `vendor-recharts` | `recharts` | Heavy charting library, only used on Analytics page |
| `vendor-react-query` | `@tanstack/react-query` | Core data fetching, used across pages |
| `vendor-zustand` | `zustand` | Global state, used across pages |
| `vendor-*` (auto) | Other `node_modules` | Rollup default splits remaining deps by package |

This ensures:
- Analytics page loads `vendor-recharts` on demand
- All pages share `vendor-react-query` and `vendor-zustand` (cached after first load)
- Initial bundle contains only Dashboard/Login + shared UI + React runtime

---

## 5. Acceptance Criteria

- [ ] `npm run build` succeeds
- [ ] `dist/stats.html` generated and viewable
- [ ] Initial gzipped bundle < 500 KB (verify via `gzip-size dist/assets/*.js` or analyzer report)
- [ ] Lazy pages load correctly on navigation (no hydration errors)
- [ ] Shared `PageLoader` shows during chunk load
- [ ] All existing tests pass (`npm run test`)

---

## 6. Testing

- Run `npm run build` → open `dist/stats.html` → verify chunk sizes
- Manual test: navigate to each lazy route, confirm spinner appears briefly
- Run full test suite: `npm run test` and `npm run test:e2e`

---

## 7. Rollback Plan

If issues arise:
- Revert `App.tsx` to eager imports
- Remove `manualChunks` and analyzer plugin
- No database/migrations affected (frontend-only change)
