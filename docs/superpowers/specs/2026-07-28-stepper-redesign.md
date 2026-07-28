# Stepper Redesign — Arcade Launcher Setup Wizard

**Date:** 2026-07-28
**Status:** Approved
**Component:** `launcher_widgets.py` → `StepIndicator` class

---

## 1. Problem Summary

The current `StepIndicator` in the Setup Wizard has visual artifacts:
- Boxy connecting lines that render as bordered rectangles instead of thin lines
- Inconsistent spacing between steps
- No clear visual differentiation between completed/current/upcoming states
- Scrollable frame implementation causes canvas/frame background bleed
- Only 1–3 steps visible at narrow widths; no horizontal scroll

---

## 2. Design Goals

| Goal | Success Criteria |
|------|------------------|
| **Clean visual hierarchy** | Three distinct states (completed/current/upcoming) instantly recognizable |
| **Modern aesthetic** | Matches launcher's indigo accent, rounded cards (RADIUS=10), dark/light mode |
| **Responsive** | All 4 steps accessible at any width; smooth horizontal scroll when needed |
| **Accessible** | Keyboard navigation, ARIA semantics, reduced-motion respect |
| **Zero artifacts** | No background bleed, no boxy lines, no layout jumps |

---

## 3. Visual Design

### 3.1 Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│  ●──────────●──────────●──────────●                                 │
│  1          2          3          4                                 │
│  Café       Staff      Seats     Override                           │
└─────────────────────────────────────────────────────────────────────┘
```

- **Pill container**: Rounded rect (height 32px, corner radius = RADIUS)
- **Step indicator**: Circle (20px) on left edge of pill
- **Label**: Text right of circle, vertically centered
- **Connecting line**: 2px line between pills, centered on circles

### 3.2 State Definitions

| Property | Completed | Current | Upcoming |
|----------|-----------|---------|----------|
| Pill background | `accent_fill` (solid indigo) | `accent_fill` | `bg_tertiary` |
| Circle content | ✓ checkmark (white) | Step number (white) | Step number (muted) |
| Circle border | none | 2px `text_on_accent` | none |
| Connecting line (to next) | `accent_fill` (filled) | `accent_fill` (filled to current) | `border` (gray) |
| Label color | `text_on_accent` (white) | `text_on_accent` (white) | `text_secondary` (muted) |
| Pill border | none | 1px `accent_fill` | 1px `border` |

### 3.3 Animations

| Animation | Duration | Easing | Trigger |
|-----------|----------|--------|---------|
| State color morph | 200ms | ease-out | `set_active()` call |
| Current pulse | 2000ms | ease-in-out | Loop on current step |
| Line fill | 200ms | ease-out | State transition |

**Reduced motion:** All animations disabled when `prefers_reduced_motion()` returns true.

---

## 4. Architecture

### 4.1 Component Structure

```
StepIndicator (CTkFrame)
├── canvas (tk.Canvas) — horizontal scroll surface
│   └── pills (CTkFrame) — placed via canvas.create_window()
└── scrollbar (CTkScrollbar) — auto-hidden when not needed
```

**Why not CTkScrollableFrame?** Direct canvas control avoids:
- Internal frame background bleed
- Geometry manager conflicts (grid vs pack)
- Scrollbar styling limitations

### 4.2 Data Flow

```
set_active(idx)
    │
    ├─► For each pill i:
    │     ├─► Determine state: completed (i < idx), current (i == idx), upcoming (i > idx)
    │     ├─► Animate pill.bg → target color
    │     ├─► Animate circle → checkmark/number
    │     ├─► Animate label.color → target
    │     └─► Animate line[i] → target color
    │
    └─► If new current step off-screen: canvas.xview_moveto()
```

---

## 5. Implementation Details

### 5.1 Public API (Unchanged)

```python
class StepIndicator:
    def __init__(self, master, fonts, steps: list[str])
    def grid(self, **kw)          # layout
    def set_active(self, idx: int)  # 0-based step index
```

### 5.2 Internal Methods

| Method | Purpose |
|--------|---------|
| `_build_pill(i, label)` | Creates pill + circle + label for step i |
| `_animate_pill(pill, target_state)` | Color morph + content swap |
| `_animate_line(i, target_state)` | Line fill animation |
| `_on_canvas_configure(e)` | Update scrollregion, show/hide scrollbar |
| `_on_mousewheel(e)` | Horizontal scroll via wheel/trackpad |

### 5.3 Constants (from `launcher_theme.py`)

```python
RADIUS = 10           # pill corner radius
PILL_HEIGHT = 32
CIRCLE_SIZE = 20
LINE_THICKNESS = 2
ANIM_DURATION = 200   # ms
PULSE_DURATION = 2000 # ms
```

---

## 6. Responsive Behavior

| Viewport Width | Behavior |
|----------------|----------|
| ≥ 520px (4 × 110 + gaps) | All pills visible, equal spacing, no scroll |
| 320–519px | Horizontal scroll enabled; scrollbar auto-shows on hover/focus |
| < 320px | Same; touch-drag scroll on touchscreens |

**Scrollbar:** Hidden by default. Appears on canvas `<Enter>` or when content overflows. Auto-hides after 1500ms of no interaction.

---

## 7. Accessibility

| Requirement | Implementation |
|-------------|----------------|
| Keyboard nav | ←/→ arrows move focus between pills; `Tab` enters/exits component |
| ARIA | `role="list"` on canvas; `role="listitem" aria-current="step"` on current pill |
| Screen readers | `aria-label="Step X of Y: Label"` on each pill |
| Reduced motion | `prefers_reduced_motion()` gates all animations |
| Focus visible | Current pill gets 2px `accent` outline when keyboard-focused |

---

## 8. Testing Checklist

- [ ] All 4 steps render correctly at default window width (780px)
- [ ] Horizontal scroll works at 400px window width
- [ ] Scrollbar appears on hover, hides after delay
- [ ] `set_active(0)` → only step 1 is "current"
- [ ] `set_active(1)` → step 1 "completed", step 2 "current"
- [ ] `set_active(3)` → steps 1–3 "completed", step 4 "current"
- [ ] Dark/light mode: colors swap correctly
- [ ] Reduced motion: no animations, instant state changes
- [ ] Keyboard: Tab → Enter/Arrows navigate pills
- [ ] No visual artifacts (background bleed, boxy lines, layout jumps)

---

## 9. Migration Notes

- **File:** `launcher_widgets.py` — replace `StepIndicator` class entirely
- **Dependencies:** None new (uses existing `launcher_theme`, `launcher_motion`)
- **Backward compat:** Public API unchanged; `SetupWizard` calls `indicator.set_active(step_idx)` as before
- **Risk:** Low — isolated widget, no data layer changes

---

## 10. Future Enhancements (Out of Scope)

- Clickable pills (jump to step) — requires wizard navigation integration
- Step validation icons (error/warning on incomplete steps)
- Vertical orientation for narrow mobile-like layouts
- Persisted scroll position across screen transitions
