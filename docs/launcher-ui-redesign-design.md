# Launcher UI Redesign — Design Spec

- **Date:** 2026-07-20
- **Status:** Approved (design); pending implementation plan
- **Component:** `launcher.py` (Arcade server launcher GUI)
- **Skill flow:** brainstorming → (this spec) → writing-plans → implementation

## 1. Context & Problem

`launcher.py` is the entry point for the Arcade server. It is a CustomTkinter app
that routes the user through three screens based on license/config state:

1. **ActivationScreen** — license missing/invalid/bound to another machine.
2. **SetupWizard** — license valid but `arcade.config.json` absent (first run).
3. **MainScreen** — ready; start/stop the FastAPI server, view logs, open dashboard.

The app is functional but visually inconsistent with the rest of the product and
lagging the more polished `tools/keygen/license_gui/` (which has a topbar,
appearance toggle, footer status bar, toasts, reusable `Card`/`LabeledField`
widgets, an Inter font loader, and a gradient accent strip).

Additional findings from exploration:

- `launcher.py` loads its theme from a dedicated `launcher_theme.py` (good
  separation) but uses a **blue `#2563EB`** palette that differs from the keygen
  GUI's **indigo `#6366F1`**.
- `launcher_theme.py` references `frontend/public/icon_opc.png` for the logo, but
  **that file does not exist** in the repo — so today's header is *text-only*
  (no logo renders).
- `motion-dev` (120fps GPU spring animations) applies to React/Next/Svelte/Astro
  only and **cannot** run in a Tkinter desktop app. Its *principles* (entrance
  reveals, hover affordances, animated state transitions, reduced-motion respect)
  are adapted instead.
- `ui-ux-pro-max:ui-styling` (shadcn/Tailwind/Radix) is web-only; its *principles*
  (design tokens, consistent components, dark mode, focus/affordance states) are
  adapted into the Python theme module.
- The brand SVG is `frontend/public/arcade_icon.svg` — a blue-gradient rounded
  square (`#0334f0 → #06a3fc`) with a white controller glyph. It is **not** a dark
  logo; on dark surfaces the blue already pops.

## 2. Goals

- Make the launcher read as a **professional SaaS** desktop app.
- Borrow the keygen GUI's UI *furniture* (topbar, appearance toggle, footer status
  bar, toasts, card/field widgets, gradient accent) and token discipline.
- Switch the accent to **indigo** and adopt a **hybrid typography** (Inter UI +
  gaming display wordmark/headers).
- Render the brand logo in dark mode as a **white controller glyph on transparent**.
- Add **tasteful, accessible micro-motion**.
- Keep all three screens' *logic* intact; only structure, styling, and polish change.
- Keep all asset/font loading **headless-safe** (guarded) so CI/imports never break.

## 3. Non-Goals (YAGNI)

- No sidebar/nav restructure — the launcher is a linear 3-step flow; a keygen-style
  sidebar does not map to it.
- No change to license verification, server process lifecycle, DB bootstrap, or
  routing logic.
- No pagination of the SetupWizard into separate "pages" — validation/fields stay
  in one scrollable form; a *visual* step indicator is added instead.
- No change to the web frontend or agent; the launcher's palette deliberately
  diverges from the web dashboard's blue (the launcher is internal/counter staff,
  and the user chose indigo for it).
- No runtime SVG dependency forced on end users (committed PNG fallbacks).

## 4. Locked Decisions

| Decision | Choice |
|---|---|
| Scope | Refresh + keygen furniture (keep linear flow) |
| Accent | Indigo `#6366F1` / `#818CF8` |
| Motion | Tasteful micro-motion (reduced-motion aware) |
| Typography | Inter (UI/body) + gaming display font (wordmark/headers) |
| Logo source | `frontend/public/arcade_icon.svg` |
| Dark-mode logo | White controller glyph on transparent (square dropped) |

## 5. Design

### §1 — Theme system (`launcher_theme.py` → token model)

Replace the flat color constants with a `COLORS` dict of `(light, dark)` tuples,
mirroring `tools/keygen/license_gui/theme.py` for cross-tool consistency. CustomTkinter
auto-selects the tuple element by appearance mode.

**Tokens (adopt keygen's exact surface/semantic values; add indigo button fills):**

| Token | Light | Dark | Role |
|---|---|---|---|
| `bg_primary` | `#F8F9FC` | `#0E0E12` | app/window background |
| `bg_secondary` | `#FFFFFF` | `#17171C` | cards, topbar, footer |
| `bg_tertiary` | `#F1F2F6` | `#202027` | insets, hover, segmented |
| `text_primary` | `#1A1A20` | `#F4F4F6` | headings/body |
| `text_secondary` | `#5B5B66` | `#A0A0AB` | muted/captions |
| `text_disabled` | `#A8A8B2` | `#5B5B66` | disabled hints |
| `text_on_accent` | `#FFFFFF` | `#FFFFFF` | text on indigo fills |
| `accent` | `#6366F1` | `#818CF8` | non-text accents (indicators, focus ring, gradient strip, links) |
| `accent_fill` | `#6366F1` | `#4F46E5` | **button/CTA fills** (white text) |
| `accent_fill_hover` | `#4F46E5` | `#4338CA` | button hover |
| `success` | `#16A34A` | `#22C55E` | running/ok |
| `warning` | `#D97706` | `#F59E0B` | busy/trial |
| `error` | `#DC2626` | `#EF4444` | stopped/error |
| `border` | `#E6E7EC` | `#2A2A32` | 1px borders |

> **Contrast rationale (WCAG AA):** `text_primary` on `bg_primary` ≈ 16:1 (light)
> and ≈ 17:1 (dark). `text_secondary` on `bg_primary` ≈ 5.9:1 / 7.5:1 — both ≥ 4.5:1.
> `text_on_accent` (white) on `accent_fill` `#6366F1` ≈ 4.6:1 (light, passes) and on
> `#4F46E5` ≈ 6.3:1 (dark, passes). The lighter dark `accent` (`#818CF8`) is used only
> for *non-text-bearing* accents (active indicator, focus ring, gradient) where text
> contrast does not apply. A dedicated `accent_fill` (darker in dark mode) guarantees
> white-button-text contrast — this is exactly the regression the dev assertion below catches.

**Shape & spacing:** `RADIUS = 10`; `SPACING = {xs:4, sm:8, md:12, lg:16, xl:24, xxl:32}`
(reuse keygen's scale). `BTN_HEIGHT = 44`.

**Fonts (hybrid):**
- `load_font_family()` — prefer a bundled `Inter-Variable.ttf` (drop beside the
  launcher) via `ctk.FontManager.load_font`; else system sans (`Segoe UI` /
  `Helvetica Neue` / `DejaVu Sans`).
- A bundled gaming display font (Chakra Petch / Russo One) loaded for the `ARCADE`
  wordmark + section headers only (the existing `_resolve_brand_font()` drop-in
  mechanism is reused; if absent, the display text falls back to Inter bold).
- Type scale: `h1` (22/bold), `h2` (15/bold), `body` (13), `body_bold` (13/bold),
  `caption` (11).

**Dev-only contrast assertion:** a `_assert_contrast()` helper in the theme module
computes WCAG luminance contrast for the critical text/bg pairs and raises in tests
if any pair drops below 4.5:1 (body) / 3:1 (large). Guarded so it never runs in the
launcher runtime — only invoked by the optional smoke test (§7).

### §2 — App shell (`LauncherApp`)

Wrap the three screens in a persistent shell built once in `LauncherApp.__init__`:

- **Topbar** (`CTkFrame`, `bg_secondary`, `corner_radius=0`):
  - Logo (left) + `ARCADE` wordmark (display font) + subtitle/context.
  - **Appearance toggle**: `CTkOptionMenu` `System` / `Dark` / `Light` →
    `ctk.set_appearance_mode(...)`. Persist the choice to a small
    `launcher.state.json` (created on first launch; never `arcade.config.json`,
    which does not exist during Activation/Setup) so it survives restart.
  - A small **status/key badge** (e.g., "License OK" / "No license") reusing the
    semantic colors.
  - **3px gradient accent strip** under the topbar (reuse
    `tools/keygen/icon/arcade_gradient_3px.png`; if absent, skip — no crash).
- **Content area** (centered, scrollable if needed) hosts the active screen via the
  existing `show_screen()` router (restyled; see §5 motion).
- **Footer** `StatusBar` (icon + message + hint), replacing ad-hoc `messagebox`
  calls where a non-blocking status is appropriate (a destructive "Confirm Exit"
  still uses a modal `messagebox`).
- **Toasts:** borderless, topmost, self-destructing, bottom-right (ported from
  keygen's `show_toast`), used for "Copied", "Server started", "Server stopped", etc.
- **Window:** grow modestly to `780×640` (keep `minsize(720, 600)`); recenter.

### §3 — Reusable widgets (`launcher_widgets.py`, new file)

Port + indigo-theme the keygen widgets (`tools/keygen/license_gui/widgets.py`):
- `Card` — `bg_secondary` fill, 1px `border`, single `RADIUS`.
- `LabeledField` — label + `CTkEntry` + inline error label; `set_error()` /
  `clear_error()`; error border uses `error` token. Used by the SetupWizard.
- `StatusBar` — thin bottom bar; icon + text + hint; icon set `● / ✓ / ✕ / ◌`
  mapped to `info / success / error / busy` (color **+** symbol → satisfies
  "never color alone").
- `Toast` — `show_toast(app, message, kind)`, kind colors `accent/success/error`
  with a leading symbol.
- `SegmentedControl` is **omitted** (no current use; YAGNI).

### §4 — Screen restyles (logic unchanged)

- **ActivationScreen**: error card uses `error` border/color **+ an error icon**
  before the headline; indigo `Browse` CTA (`accent_fill`); HWID field + "Copy"
  button → toast instead of `messagebox`.
- **SetupWizard**: each section ("Café & Server", "Staff Accounts", "Seats") becomes
  a `Card` containing `LabeledField`s. **Add a top step indicator** (see ★A below):
  three numbered chips joined by a progress line that highlights the section
  currently in view as the user scrolls (visual only; no pagination, no logic change).
  Inline validation via `LabeledField.set_error()` (e.g., non-numeric seat count,
  empty required field, PIN outside 4–6 digits) with clear, actionable messages.
  Primary CTA "Finish Setup" uses `accent_fill` (was emerald — now indigo for
  consistency; success/start actions elsewhere keep `success`).
- **MainScreen**: status **pill** gets a leading glyph (● running / ■ stopped) **+**
  text, color from `success`/`error`. Buttons: **Start Server → `success`** (the "go"
  action, green), **Stop → `error`** (red), **Dashboard → `bg_tertiary`** (neutral).
  Log panel wrapped in a `Card`. Start/stop fires a toast + the animated pill (§5).
  (The *onboarding* primary CTAs — Browse, Finish Setup — use `accent_fill` indigo;
  the runtime Start control stays green for "go" semantics.)

> **★A Step indicator (from wizard UX research):** a `CTkFrame` row of 3 chips
> (`1 Café`, `2 Staff`, `3 Seats`) with a connecting line; the active chip is filled
> with `accent_fill` and the connecting line fills up to the active section. Driven by
> the scrollable form's `yview` / focus events — no change to field storage or
> `_finish()` logic.

### §5 — Motion (tasteful, reduced-motion aware)

From the CustomTkinter animation discussion: the draw engine cannot animate two
containers at once without stutter, so animations are **short and sequential**.

- **Entrance fade-in:** when `show_screen()` swaps screens, fade the *outgoing* screen
  out (container `attributes('-alpha')` 1→0 over ~180ms via `after()`), `destroy()` it,
  then fade the *incoming* screen in (0→1 over ~200ms). Never animate both together.
- **Hover affordances:** rely on CustomTkinter's built-in `hover_color` transitions
  for buttons/entries.
- **Animated status pill:** on start/stop, cross-fade the pill color and swap the
  leading glyph + label (sequential, not parallel).
- **Toast slide-in:** toast fades + nudges up into place, then self-destructs.
- **`prefers_reduced_motion()`:** read the OS setting once at startup (Windows:
  `SystemParametersInfo(SPI_GETCLIENTAREAANIMATION)` / registry fallback; macOS/Linux:
  best-effort). If set, **skip all fades** and show screens/state instantly.

### §6 — Logo (`load_logo`, revised)

- **Source of truth:** `frontend/public/arcade_icon.svg`.
- **Rasterize** to a PIL `RGBA` of size N (logo 44, topbar 40) via `cairosvg`
  (`svg2png`) when importable.
- **Light image:** rasterize the SVG as-is → blue-gradient square + white glyph.
- **Dark image:** transform the SVG source string — set the gradient `<rect>` fill to
  `none` (drop the square), keep the white controller glyph → **white glyph on
  transparent**; rasterize. (Leaves the gradient `<defs>` unused — harmless.)
- **Fallback:** commit `arcade_logo_light.png` (blue) and `arcade_logo_white.png`
  (white glyph) next to the launcher. If `cairosvg` is unavailable, `load_logo` loads
  these PNGs instead. Guarantees the logo works on low-end Windows PCs with no extra
  dependency. Both images passed to `CTkImage(light_image=, dark_image=)` so
  CustomTkinter auto-switches by appearance mode.
- **Headless-safe:** all PIL/cairosvg/asset access is `try/except`-guarded; on any
  failure `load_logo` returns `None` and callers fall back to the text-only header
  (the launcher must still open).
- Fixes the broken `icon_opc.png` reference.

> Note: if the brand later switches to the blue-gradient product logo *as* the dark
> variant, a white silhouette would render as a white blob — in that case supply a
> dedicated `arcade_logo_white.png` (transparent square, white glyph) instead of the
> SVG transform. The fallback path already supports this.

### §7 — Verification

- All logo/font/asset loading remains guarded (as today) so imports and headless CI
  never break.
- **Manual Windows smoke test** (target OS): launch → Activation screen renders with
  logo; toggle `Dark` → logo becomes white glyph, surfaces go dark; run SetupWizard
  with a bad PIN / non-numeric seat count → inline errors; complete setup → MainScreen;
  Start Server → toast + animated pill (● running, success color); Stop → toast + pill
  (■ stopped, error color); Open Dashboard opens browser; toggle appearance persists on
  restart.
- **Optional smoke test** (`pytest`): import `launcher_theme`; assert all critical
  text/bg token pairs meet WCAG thresholds via `_assert_contrast()`; assert
  `load_logo` returns a `CTkImage` when the SVG/PNG is present and `None` when assets
  are absent (headless).

## 6. File-by-File Change List

| File | Change |
|---|---|
| `launcher_theme.py` | Replace flat constants with `COLORS` token dict + `SPACING`; add `accent_fill`/`accent_fill_hover`/`text_on_accent`; indigo; Inter + display fonts; `load_logo` SVG rasterize + dark-white transform + PNG fallback; `_assert_contrast()`. |
| `launcher_widgets.py` | **New**: `Card`, `LabeledField`, `StatusBar`, `Toast` (indigo-themed ports of keygen widgets). |
| `launcher.py` | Add topbar (logo, wordmark, appearance toggle + persistence, badge, gradient strip), footer `StatusBar`, `Toast` system, content area; restyle three screens with new tokens/widgets; add SetupWizard step indicator; wire motion (sequential fades, animated pill); replace some `messagebox` with toasts. Screen *logic* unchanged. |
| `frontend/public/arcade_icon.svg` | Used as logo source (no edit needed). |
| `arcade_logo_light.png`, `arcade_logo_white.png` | **New (committed)**: PNG fallbacks generated from the SVG. |
| `tools/keygen/icon/arcade_gradient_3px.png` | Reused for the topbar gradient strip (no edit). |

## 7. Risks & Mitigations

- **cairosvg on Windows:** mitigated by committed PNG fallbacks + headless-safe guards.
- **Animation jank on old hardware:** mitigated by short sequential fades + reduced-motion guard.
- **Indigo diverges from web dashboard blue:** intentional (user choice); documented in §3 Non-Goals.
- **Display font absent:** falls back to Inter bold (no crash).
- **Gradient strip / Inter font absent:** skipped gracefully.

## 8. Out of Scope / Future

- Sidebar nav (not applicable to linear flow).
- Paginated wizard.
- Syncing the web frontend to indigo (separate decision).
- Animated SVG/Canvas effects analogous to `motion-dev` (not feasible in Tkinter).
