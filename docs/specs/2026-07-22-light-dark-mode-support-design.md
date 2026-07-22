# Light/Dark Mode Support for Frontend Pages (Excluding Login)

## 1. Overview

**Goal**: Add light/dark mode support to all authenticated pages (Dashboard, Members, Analytics, Events, Settings) while keeping the Login page's existing independent theme system unchanged. Additionally, make the NavShell logo (sidebar + mobile header) a clickable theme toggle.

**Scope**: Frontend only (`frontend/src/`). No backend changes.

**Current State**:
- **Login page** (`/`): Has its own theme (`light`/`dark`) stored in `localStorage` key `arcade-login-theme`, toggled via the centered logo button. Uses CSS `.login-root[data-theme="..."]` selectors that override root CSS variables.
- **Authenticated pages** (`/`, `/members`, `/analytics`, `/events`, `/settings`): Currently render with root `:root` (light) variables only. The `.dark` class on `:root` is defined in CSS but never applied.
- **NavShell**: Logo is decorative (`<Icon name="GamepadDirectional" size={32} />`) — not clickable.

## 2. Architecture

### 2.1 Theme State Management

Create a new Zustand store: `frontend/src/store/themeStore.ts`

```typescript
// frontend/src/store/themeStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'light' | 'dark';

interface ThemeStore {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
  initialize: () => void;
}

const THEME_KEY = 'arcade-app-theme';

function getInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'dark';
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  // Fallback to system preference
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set, get) => ({
      theme: getInitialTheme(),

      toggleTheme: () => {
        const newTheme = get().theme === 'dark' ? 'light' : 'dark';
        set({ theme: newTheme });
        applyTheme(newTheme);
      },

      setTheme: (theme: Theme) => {
        set({ theme });
        applyTheme(theme);
      },

      initialize: () => {
        applyTheme(get().theme);
      },
    }),
    {
      name: THEME_KEY,
      onRehydrateStorage: () => (state) => {
        if (state) state.initialize();
      },
    }
  )
);
```

**Key Design Decisions:**
- **Separate storage key** (`arcade-app-theme`) from login (`arcade-login-theme`) so themes are independent
- **System preference fallback** on first visit (no stored value)
- **`persist` middleware** handles localStorage sync automatically
- **`applyTheme`** toggles `.dark` class on `<html>` element — this activates the existing `.dark` CSS variable block in `index.css`
- **`initialize()`** called on hydration to apply theme before first paint (prevents flash)

### 2.2 App Bootstrap Integration

Modify `frontend/src/App.tsx` to initialize theme on mount:

```tsx
// frontend/src/App.tsx (additions marked with // ★)
import { useEffect } from 'react';
import { useThemeStore } from '@/store/themeStore'; // ★

export default function App() {
  useFeatureFlags();
  const initializeTheme = useThemeStore((s) => s.initialize); // ★

  useEffect(() => {
    initializeTheme(); // ★
  }, [initializeTheme]); // ★

  return (
    // ... existing routes
  );
}
```

**Why in `App.tsx`?** It's the root component that wraps all routes (including login), so theme is applied globally. The login page's `.login-root[data-theme]` selectors have higher specificity and will override root variables — preserving login theme independence maintained automatically.

### 2.3 NavShell Logo as Theme Toggle

Modify `frontend/src/components/NavShell.tsx`:

1. **Add imports**:
```tsx
import { useReducedMotion } from 'motion/react';
import { motion } from 'motion/react';
import { useThemeStore } from '@/store/themeStore';
import { Icon } from '@/components/ui/Icon';
```

2. **Add theme state & toggle**:
```tsx
export function NavShell({ children }: { children: ReactNode }) {
  const flags = useFeatureFlagStore((s) => s.flags);
  const items = NAV.filter((n) => !n.flag || flags[n.flag]);
  const [menuOpen, setMenuOpen] = useState(false);
  const theme = useThemeStore((s) => s.theme); // ★
  const toggleTheme = useThemeStore((s) => s.toggleTheme); // ★
  const reduceMotion = useReducedMotion(); // ★
  // ... existing logout, navigate
```

3. **Replace sidebar logo** (lines 58-61):
```tsx
{/* Sidebar logo — theme toggle ★ */}
<motion.button
  type="button"
  onClick={toggleTheme}
  aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
  aria-pressed={theme === 'dark'}
  title="Toggle theme"
  whileHover={reduceMotion ? undefined : { scale: 1.04 }}
  whileTap={reduceMotion ? undefined : { scale: 0.96 }}
  className="mx-auto flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-border/60 bg-card/40 shadow-lg backdrop-blur-sm outline-none transition-colors hover:bg-card/60 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
>
  <motion.span
    animate={{ rotate: theme === 'dark' ? 0 : 180 }}
    transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 220, damping: 20 }}
    className="flex items-center justify-center"
  >
    <Icon
      name="GamepadDirectional"
      size={32}
      variant="stroke"
      motion="none"
      className="text-foreground transition-colors duration-500"
      aria-hidden={true}
    />
  </motion.span>
</motion.button>
```

4. **Replace mobile header logo** (lines 74-78):
```tsx
<div className="flex items-center gap-2">
  <motion.button
    type="button"
    onClick={toggleTheme}
    aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
    aria-pressed={theme === 'dark'}
    title="Toggle theme"
    whileHover={reduceMotion ? undefined : { scale: 1.04 }}
    whileTap={reduceMotion ? undefined : { scale: 0.96 }}
    className="flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
  >
    <motion.span
      animate={{ rotate: theme === 'dark' ? 0 : 180 }}
      transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 220, damping: 20 }}
      className="flex items-center justify-center"
    >
      <Icon
        name="GamepadDirectional"
        size={28}
        variant="stroke"
        motion="none"
        className="text-foreground transition-colors duration-500"
        aria-hidden={true}
      />
    </motion.span>
  </motion.button>
  <h1 className="text-lg font-bold text-foreground">Arcade</h1>
</div>
```

5. **Replace Sheet header logo** (lines 92-96):
```tsx
<div className="flex items-center gap-2 px-3 py-2">
  <motion.button
    type="button"
    onClick={toggleTheme}
    aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
    aria-pressed={theme === 'dark'}
    title="Toggle theme"
    whileHover={reduceMotion ? undefined : { scale: 1.04 }}
    whileTap={reduceMotion ? undefined : { scale: 0.96 }}
    className="flex h-12 w-12 items-center justify-center rounded-full border border-border/60 bg-card/40 shadow-lg backdrop-blur-sm outline-none transition-colors hover:bg-card/60 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
  >
    <motion.span
      animate={{ rotate: theme === 'dark' ? 0 : 180 }}
      transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 220, damping: 20 }}
      className="flex items-center justify-center"
    >
      <Icon
        name="GamepadDirectional"
        size={32}
        variant="stroke"
        motion="none"
        className="text-foreground transition-colors duration-500"
        aria-hidden={true}
      />
    </motion.span>
  </motion.button>
  <h1 className="text-lg font-bold text-foreground">Arcade</h1>
</div>
```

**Consistency**: All three logo locations (sidebar, mobile header, sheet header) use identical toggle behavior, icon animation, and accessibility attributes.

## 3. Affected Files

| File | Change Type |
|------|-------------|
| `frontend/src/store/themeStore.ts` | **NEW** - Theme state management |
| `frontend/src/App.tsx` | Add `useEffect` to initialize theme |
| `frontend/src/components/NavShell.tsx` | Replace 3 logo instances with animated toggle buttons |
| `frontend/src/index.css` | No changes (existing `.dark` class variables already defined) |

## 4. Testing Strategy

### 4.1 Unit Tests

**`themeStore.test.ts`**:
- `getInitialTheme` returns `'dark'` when no localStorage + system prefers dark
- `getInitialTheme` returns `'light'` when no localStorage + system prefers light
- `toggleTheme` flips theme and calls `applyTheme`
- `persist` middleware saves to `arcade-app-theme`
- Hydration calls `initialize()` and applies theme

**`NavShell.test.tsx`**:
- Sidebar logo button toggles theme store
- Mobile header logo button toggles theme store
- Sheet header logo button toggles theme store
- `aria-label` and `aria-pressed` update correctly
- Icon rotates 180° on theme change (snapshot test)

### 4.2 Integration / Visual Tests

- **Light mode**: All settings tabs, Dashboard, Members, Analytics, Events render with light CSS variables
- **Dark mode**: Same pages render with dark CSS variables
- **Login page isolation**: Toggle theme on login page → only login page changes; navigate to dashboard → dashboard uses app theme, not login theme
- **Persistence**: Refresh page → theme preserved
- **Focus-visible**: Tab to logo → focus ring visible
- **Reduced motion**: `prefers-reduced-motion` disables scale/rotate animations

### 4.3 Accessibility Checklist

- [ ] `aria-label` describes action ("Switch to light theme" / "Switch to dark theme")
- [ ] `aria-pressed` reflects current state
- [ ] `role="button"` (native `<button>`)
- [ ] Keyboard focusable (`tabIndex=0` by default)
- [ ] Focus indicator visible (`focus-visible:ring-2`)
- [ ] Color contrast meets WCAG AA in both themes (existing tokens already compliant)

## 5. Implementation Order

1. Create `frontend/src/store/themeStore.ts` with tests
2. Update `frontend/src/App.tsx` to initialize theme
3. Update `frontend/src/components/NavShell.tsx` (three logo locations)
4. Add/update tests
5. Run `npm run lint` and `npm test` in frontend
6. Manual visual verification in both themes across all pages

## 6. Acceptance Criteria

- [ ] Login page theme unchanged, independent
- [ ] Dashboard, Members, Analytics, Events, Settings support light/dark
- [ ] NavShell logo (sidebar, mobile header, sheet header) toggles theme
- [ ] Theme persists in `localStorage` key `arcade-app-theme`
- [ ] No flash of wrong theme on load
- [ ] Animations respect `prefers-reduced-motion`
- [ ] Accessibility attributes correct
- [ ] All existing tests pass
- [ ] Code passes `ruff`, `mypy`, `npm run lint`

## 7. Rollback Plan

If issues arise:
1. Revert `NavShell.tsx` logo changes
2. Remove `themeStore.ts` and `App.tsx` initialization
3. Delete `arcade-app-theme` from localStorage via DevTools
4. App returns to light-only (current state)

---

*Spec Version: 1.0 | Date: 2026-07-22*
