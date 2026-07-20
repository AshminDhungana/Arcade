# Agent Broadcast Overlay Redesign — Design Spec

- **Date:** 2026-07-20
- **Status:** Approved (design); pending implementation plan
- **Component:** `agent/` (Arcade Agent — kiosk lock screen + in-session HUD + modals)
- **Skill flow:** brainstorming → (this spec) → writing-plans → implementation
- **Related:** `docs/launcher-ui-redesign-design.md` (the team's most recent design work; this spec mirrors its structure and its "adapt the skill's principles" discipline)

## 1. Context & Problem

The Arcade Agent renders two overlay surfaces over each gaming PC, both built as **plain vanilla DOM/TypeScript** (no framework):

1. **Kiosk overlay** (`index.html` → `index.ts` → `components/kiosk-overlay.ts` + `kiosk.css`) — the full-screen, `kiosk:true` lock/lobby screen shown when **no** session is active. Blocks desktop access.
2. **HUD** (`hud.html` → `hud.ts` + `hud.css`) — the transparent, always-on-top, **click-through** overlay shown *during* a session, over the live game.

Plus two **modal** surfaces shared (and currently *duplicated*) by both: the low-time warning (`components/low-time-warning.ts`) and the staff-override PIN pad (`components/staff-override-dialog.ts`).

The overlays are functional but visually behind the rest of the product:

- Hard-coded **cyan `#4fc3f7`** on near-black `#0a0a0f`, with **no design tokens** — colors and sizes are scattered literals.
- Inconsistent with the product's emerging design language: the **web frontend** uses blue `#0090fa` + Inter + a token system + a neon-grid login backdrop; the **launcher** was just redesigned to **indigo** `#6366F1`. The agent is the third, ad-hoc palette.
- The in-session HUD currently shows a **persistent centered timer** that sits over the game the whole session — intrusive and not "tournament-ready."

Findings from code exploration (verified, see §10 appendix):

- The kiosk and HUD **toggle automatically** with the session: `hideKioskOverlay()` (fired on session start) calls `showHud()`; `showKioskOverlay()` calls `hideHud()` (`windows.ts:35,99-101`). No extra plumbing needed to treat them as two surfaces.
- `LOW_TIME_WARNING` already carries `minutes_remaining` and is routed to the active window (`ws/types.ts:98`, `windows.ts:143-148`) — so a local countdown needs **no WebSocket contract change**.
- `updateTimer` payload is `{ elapsedSeconds }` only; `remainingSeconds` is a planned future add (Epic 6.5.4), confirming a *local* countdown is the right call for now.
- Click-through already works: `setIgnoreMouseEvents(true,{forward:true})` + CSS `pointer-events` (`windows.ts:127`, `hud.css`).
- Vitest tests already exist for `kiosk-overlay`, `low-time-warning`, `hud`, `staff-override-dialog`.

## 2. Goals

- Give the agent a **distinct broadcast/esports identity** — electric cyan/violet accent, heavy gaming display type, near-black high-contrast base, bold scoreboard chrome + glow — so the cafe screen looks professional and "on air" while hosting a tournament.
- Make the **kiosk lock screen** the full broadcast showcase.
- Make the **in-session HUD** respectful of gameplay: a **transient** timer (brief at session start, then hidden), **only notifications** during play, and the timer **returning urgently in the final ~5 minutes**. Never disturb the player.
- Unify the **modals** into one broadcast "card" treatment and de-duplicate their CSS.
- Introduce a **shared design-token layer** so the agent stops using scattered literals.
- Add an **optional, server-controlled event banner** on the kiosk (hidden by default; set during tournaments from the dashboard).
- Keep all **logic/contracts intact**; only structure, styling, motion, and one optional field change.
- Stay **dependency-free** in the renderer (no React, no `motion-dev` import). Adapt the `ui-ux-pro-max` and `motion-dev` *principles* (as the launcher redesign did for its web-only skills).

## 3. Non-Goals (YAGNI)

- **No real match/team/score data** on screen — this is a broadcast *look*, not a tournament data feed. (A placeholder banner slot is data-driven but shows cafe/event text only.)
- **No React / motion-dev dependency.** Motion.dev's React API cannot run in the vanilla renderer; its principles are adapted into CSS + the Web Animations API.
- **No WebSocket contract change** for the timer — the HUD countdown is local from `minutes_remaining`. (Swap to server `remainingSeconds` later if Epic 6.5.4 lands.)
- **No re-theme of the web frontend or launcher** — the agent deliberately keeps its own identity (per user choice), diverging from the web's blue and the launcher's indigo.
- **No change** to session lifecycle, kiosk hardening, screenshot, restart/shutdown, or IPC security model.
- **No kiosk/HUD framework migration** — they stay plain DOM.

## 4. Locked Decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Scope | Broadcast-grade *aesthetic* (no real match data) |
| 2 | Identity | Distinct broadcast identity — electric cyan/violet, gaming display type, near-black, scoreboard chrome + glow |
| 3 | Surfaces | Unified — kiosk + HUD + modals |
| 4 | Motion | CSS chrome + Web Animations API for timers (no new dependency) |
| 5 | Composition | Kiosk-heavy / HUD-light; in-session HUD is transient + notification-only |
| 6 | Event banner | Optional `eventBanner` field; **hidden by default**; **server-controlled** (dashboard setting); agent is a passive renderer |

## 5. Design

### §1 — Design tokens (new `renderer/tokens.css`)

A single CSS-custom-property layer, imported by both surfaces (and the shared modal/base styles), replacing the hard-coded `#4fc3f7` / `#0a0a0f`.

| Token | Value | Role |
|---|---|---|
| `--bg-0` | `#050609` | kiosk base (near-black) |
| `--bg-1` | `#0b0e15` | panels / modal surface |
| `--bg-2` | `#141926` | insets, hover |
| `--accent` | `#22d3ee` | electric cyan (replaces `#4fc3f7`) |
| `--accent-2` | `#a855f7` | violet (gradient partner) |
| `--live` | `#ef4444` | LIVE dot / critical |
| `--warn` | `#f59e0b` | low-time amber |
| `--text-1` | `#f8fafc` | headings/body (~18:1 on `--bg-0`) |
| `--text-2` | `#9aa6b8` | muted (~8:1, passes WCAG AA) |
| `--text-3` | `#5b6678` | faint/captions |
| `--border` | `rgba(255,255,255,.08)` | hairlines |
| `--glow` | `0 0 24px` | broadcast glow |
| `--radius` | `14px` | card radius |
| `--grad` | `linear-gradient(135deg,#22d3ee,#a855f7)` | edges, LIVE bug, glows |
| `--font-display` | `'Chakra Petch','Russo One',system-ui` | wordmark, timer, headers |
| `--font-ui` | `'Inter',system-ui` | labels, body |

**Contrast rationale (WCAG AA):** `text-1` `#f8fafc` on `bg-0` `#050609` ≈ 18:1; `text-2` `#9aa6b8` on `bg-0` ≈ 8:1 (both ≥ 4.5:1). `--accent` `#22d3ee` is used for large/non-text elements (timer, glow, button border) where text contrast does not apply; small button *labels* use `text-1` on the accent fill. A contrast assertion (mirroring the launcher's `_assert_contrast()`) guards the critical pairs in an optional smoke test.

### §2 — Kiosk lock screen (full broadcast showcase)

Shown when idle / locked / session-ended. Rich, "on air" presence.

```
┌─ ARCADE ──────────── ● LIVE ──────────┐   top bug: gradient wordmark + status
│                                       │
│        [ CAFE / EVENT NAME ]          │   hero wordmark, glow
│        (event banner — only if set)   │   ◂ server-controlled, hidden by default
│                                       │
│             14 : 32                   │   live clock, display font, glow
│                                       │
│   ── status rail ──   [ CALL STAFF ]  │   bottom rail + broadcast button
└───────────────────────────────────────┘
```

- **Top bug:** gradient `ARCADE` wordmark (left) + a `● LIVE` status pill (right, red dot pulse) reflecting session/status.
- **Hero:** cafe name (from `OverlayContent.cafeName`); the optional **event banner** line renders *only* when `eventBanner` is non-empty (see §7).
- **Clock:** live local time, display font, glow (the lobby's existing clock, restyled).
- **Bottom rail:** status text (e.g., "Open · N seats") + a broadcast-style **Call Staff** button (glow + hover lift).
- Elements **stagger-fade-up** on show (entrance motion, §5).

### §3 — HUD (in-session, over the game) — transient state machine

Click-through everywhere except controls. **No persistent timer.** Driven by a small pure state machine (`hud-state.ts`) so transitions are testable.

```
state machine:
  INTRO   (session start / HUD window created)
     └─ timer(elapsed) ~5s + Call Staff 30s, entrance anim → fade → AMBIENT
  AMBIENT (playing)
     └─ nothing persistent; only ephemeral notifications:
          • announcement lower-third slides in/out (SHOW_MESSAGE)
          • (future) modals
  URGENT  (on LOW_TIME_WARNING, ~5 min left)
     └─ timer reappears, LOCAL countdown from minutes_remaining,
        urgent styling (amber→red, pulse), persistent to session end
        + low-time modal appears (dismissible)
  ENDED   (hideHud) → reset to INTRO for next session
```

- **On-screen during AMBIENT:** essentially invisible — no timer, no Call Staff. Only ephemeral notifications (the announcement lower-third) appear when relevant. This is the "should not disturb the user" guarantee; clicks pass through to the game.
- **INTRO:** the timer (elapsed, from `overlay:timer`) shows for ~5s with an entrance animation; the **Call Staff** button shows for **30 s** — then both fade to AMBIENT.
- **URGENT:** on `overlay:low-time`, the timer returns and counts down locally from `minutes_remaining * 60` (reusing `low-time-warning`'s `formatCountdown` pattern — no contract change), with urgent amber→red styling and a pulse, persistent until the session ends; the low-time modal also appears (dismissible); Call Staff stays visible.

**Call Staff visibility (HUD):** the button is intentionally scarce so it never distracts from the game:
- **INTRO** — visible for **30 s** after unlock, then hides.
- **AMBIENT (playing)** — **hidden by default.**
- **Corner hover** — when the player moves the mouse into the **bottom-right corner** hotzone, the button appears for **10 s**, then hides (re-armable on each entry).
- **URGENT** — visible (session ending; controls stay available).

*Detection:* the HUD is click-through (`setIgnoreMouseEvents(true,{forward:true})`). Hover is detected via `mousemove` delivered to the HUD under `forward:true`; if a platform does not deliver `mousemove` to an ignoring window, fall back to a small bottom-right hotzone that toggles `setIgnoreMouseEvents(false)` while hovered (the Electron "spotlight" pattern), restoring click-through on `mouseleave`. Clicking the button itself already works (button has `pointer-events:auto`).

### §4 — Modals (low-time + staff override) — broadcast restyle

Extract the currently **duplicated** `.modal-overlay` / `.modal-content` rules (present in both `kiosk.css` and `hud.css`) into the shared token layer. Restyle as broadcast "cards": `--bg-1` surface, gradient accent edge, glowing title, display-font numerals. Low-time countdown keeps its local `formatCountdown` logic; the staff-override PIN pad gets the same treatment (display-font dots, `--bg-2` keys, accent hover).

### §5 — Motion system (CSS + Web Animations API, no deps)

- **Entrance** (CSS `@keyframes`, staggered delays): kiosk elements rise + fade; HUD INTRO timer slides/fades in.
- **Timer tick** (WAAPI, `motion.ts` helper): subtle scale/opacity pulse on the changed digit group each second — alive but calm.
- **Low-time** (CSS): color crossfade cyan→amber→red + pulse.
- **Announcement** (CSS): lower-third slide-in from bottom, auto-dismiss.
- **Hover** (CSS transitions): Call Staff / buttons glow + lift.
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` disables all non-essential motion (timers still update, just no pulse). Renderer-level — respects the OS setting via Electron's Chromium.

### §6 — Typography & fonts

Reuse the product's display font (**Chakra Petch** / Russo One — same family the launcher adopted via `_resolve_display_font()`) for wordmark/timer/headers; **Inter** for UI/body. Bundle `ChakraPetch.woff2` + `Inter.woff2` in `renderer/public/`, `@font-face` them with a **system fallback** (timer falls back to a tabular system sans/mono) so a missing font never breaks layout. Headless-safe, like the launcher's asset guards.

### §7 — Event banner (server-controlled, hidden by default)

- Add **optional** `eventBanner?: string` to `OverlayContent` (`platform/types.ts`) — backward-compatible.
- The **server** owns the value (a dashboard Settings field, e.g., "Weekend Tournament"). The agent fetches it like `cafeName` (a `getEventBanner?.()` getter in `HandlerDeps`, populated in `SHOW_OVERLAY` / `FORCE_OVERLAY_ON`) and passes it through `OverlayContent`.
- The kiosk **renders the banner only when `eventBanner` is non-empty**; hidden otherwise. **No banner text is hard-coded in the agent** — the agent is a passive renderer. This satisfies "add it, hide it by default, control it from the server."

### §8 — Implementation architecture

| File | Change |
|---|---|
| `renderer/tokens.css` | **New:** all design tokens + shared modal/base styles |
| `renderer/motion.ts` | **New:** WAAPI helpers (`reveal`, `pulseTimer`, `countdown`) |
| `renderer/hud-state.ts` | **New:** pure HUD state machine (`INTRO→AMBIENT→URGENT`) — testable |
| `renderer/kiosk-overlay.ts` | add `setEventBanner(text?)` (show/hide); use tokens; broadcast layout |
| `renderer/kiosk.css` | restyle to broadcast layout; drop duplicated modal CSS (now in tokens.css) |
| `renderer/hud.ts` | wire `hud-state.ts`; transient timer + minimal layout; click-through |
| `renderer/hud.css` | restyle; drop duplicated modal CSS; Call Staff per §3 (INTRO / corner-hover / URGENT) |
| `renderer/low-time-warning.ts` | broadcast restyle; reuse shared modal CSS |
| `renderer/staff-override-dialog.ts` | broadcast restyle; reuse shared modal CSS |
| `renderer/index.html`, `renderer/hud.html` | add `<link>` to `tokens.css` (+ fonts) |
| `renderer/public/*.woff2` | **New:** bundled Chakra Petch + Inter fonts |
| `main/platform/types.ts` | add `eventBanner?: string` to `OverlayContent` |
| `main/ws/commands.ts` | populate `eventBanner` in `SHOW_OVERLAY` / `FORCE_OVERLAY_ON` via `getEventBanner?.()`; add to `HandlerDeps` |
| `renderer/preload.ts` | `OverlayData` gains `eventBanner?` (renderer side) |
| `frontend/` (dashboard) | **New:** Settings field to set/clear the event banner (server-backed) |
| `backend/` | **New:** settings value backing the event banner (read by agent via `getEventBanner`) |

No React, no `motion-dev` dependency, no timer WebSocket contract change.

### §9 — Testing & verification

- Keep/extend pure-function tests: `formatElapsed`, `formatCountdown`.
- **New:** vitest coverage for `hud-state.ts` transitions (intro→ambient→urgent, reduced-motion flag, reset on end).
- Manual smoke (target OS — Windows): start session → HUD timer shows ~5s then hides; play → no timer, clicks pass to game; server sends low-time at ~5 min → urgent timer returns + modal; announcement lower-third slides in; `Ctrl+Shift+O` staff override works; Call Staff captures only its own clicks; kiosk shows event banner **only** when the server setting is populated, hidden otherwise.
- Optional contrast assertion: tokens meet WCAG AA (mirrors launcher).
- Reduced-motion: verify no animation jank; timers still update.

### §10 — Risks & Mitigations

- **Font files missing / load failure:** mitigated by system fallback (timer uses tabular system sans/mono); never blocks layout. Bundle woff2 so low-end PCs need no network.
- **Animation jank on old hardware:** mitigated by short CSS transitions + reduced-motion guard; WAAPI only on the lightweight timer digit pulse.
- **HUD obscures gameplay:** mitigated by the transient state machine — no persistent timer in AMBIENT; click-through preserved.
- **Banner always-on (regression):** mitigated by render-if-present logic + a test asserting it's hidden when `eventBanner` is empty.
- **Agent diverges from web/launcher palettes:** intentional (user choice); documented in §3 Non-Goals.

### §11 — Out of Scope / Future

- Real tournament data (team names, scores, brackets) — would need backend event/tournament models.
- Server `remainingSeconds` in `updateTimer` (Epic 6.5.4) — could replace the local countdown.
- Animated SVG/Canvas broadcast effects analogous to full Motion.dev (not feasible in the vanilla renderer; principles adapted only).

## Appendix — Verification of load-bearing claims

| Claim | Verdict | Evidence |
|---|---|---|
| HUD appears during session | ✅ | `hideKioskOverlay()` → `showHud()` (`windows.ts:99-101`); `showKioskOverlay()` → `hideHud()` (`windows.ts:35`) |
| `LOW_TIME_WARNING` carries `minutes_remaining` | ✅ | `ws/types.ts:98`; routed to HUD (`windows.ts:143-148`) |
| No contract change needed (local countdown) | ✅ | `updateTimer` is `{ elapsedSeconds }` only; `remainingSeconds` is future (`types.ts:104-106`) |
| Modal CSS duplicated | ✅ | `.modal-overlay`/`.modal-content` in both `kiosk.css` + `hud.css` |
| Display font real (Chakra Petch/Russo One) | ✅ | `launcher_theme.py:_resolve_display_font()` |
| Test files exist (vitest) | ✅ | `kiosk-overlay.test.ts`, `low-time-warning.test.ts`, `hud.test.ts`, `staff-override-dialog.test.ts` |
| Click-through works | ✅ | `setIgnoreMouseEvents(true,{forward:true})` + CSS `pointer-events` (`windows.ts:127`, `hud.css`) |
| `docs/superpowers/` is gitignored | ✅ | `.gitignore:16`; spec saved to `docs/agent-broadcast-overlay-design.md` per repo convention |
