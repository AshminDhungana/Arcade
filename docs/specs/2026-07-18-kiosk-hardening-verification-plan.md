# Epic 7.3 — Cross-Platform Kiosk Hardening Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author a consolidated cross-platform kiosk-shortcut breakout verification matrix and a known-limitations summary, so the agent's hardening is provably verified (or honestly documented as unblockable) on Windows, macOS, and Linux.

**Architecture:** Pure documentation deliverable. One new QA artifact (`docs/agent-kiosk-verification.md`) holds the full matrix; `docs/agent-setup.md` gains a "Kiosk Hardening & Known Limitations" section summarizing only the unblockable gaps and linking the matrix. No agent source is touched — this epic verifies, it does not implement.

**Tech Stack:** Markdown only. Verification uses a Markdown renderer (GitHub / IDE preview) and `grep` for acceptance checks. No build, no test runner.

## Global Constraints

- **No `agent/` source modified.** This epic is verify-only; if a closable-but-unblocked gap is found, file a follow-up ticket instead of editing code.
- **Disposition taxonomy** — every matrix row uses exactly one of: `BLOCKED (app)`, `BLOCKED (kiosk)`, `GAP`.
- **macOS rows are gated:** authored against the Epic 7.1 design; each macOS `Result` cell pre-filled `N/A` with a "Gate: 7.1" note. Do not mark macOS rows `PASS`/`FAIL` in this epic.
- **Every `GAP` row carries a remediation or an explicit "no remediation" statement.**
- **`docs/agent-setup.md` gap summary lists all `GAP` rows and links the matrix** (`docs/agent-kiosk-verification.md`).
- **Coverage:** every Epic 7.3 todo item AND every vector in `docs/references/ARCH-02-kiosk-mode-validation.md` must appear as a matrix row.
- Reference docs: `docs/specs/2026-07-18-kiosk-hardening-verification-design.md` (design), `docs/references/ARCH-02-kiosk-mode-validation.md`, `docs/specs/2026-07-18-macos-platform-design.md` (Epic 7.1 §3).

---

### Task 1: Author `docs/agent-kiosk-verification.md` (full matrix)

**Files:**
- Create: `docs/agent-kiosk-verification.md`

**Interfaces:**
- Produces: the canonical matrix consumed by Task 2 (link target) and Task 3 (acceptance check). Later tasks read this file by path only.

- [ ] **Step 1: Create the matrix document**

Create `docs/agent-kiosk-verification.md` with exactly this content (the `Result` column is intentionally left blank for Windows/Linux; macOS rows are pre-set to `N/A`):

````markdown
# Agent Kiosk Hardening Verification Matrix

> Cross-platform verification of the Arcade Agent's kiosk shortcut hardening.
> Part of Epic 7.3. Design spec: `./specs/2026-07-18-kiosk-hardening-verification-design.md`.

## How to use

1. Capture the test environment (template below) for each run.
2. For each row, perform the **Verification step** on real hardware running the café's target OS.
3. Fill the **Result** cell: `PASS` (matches Expected), `FAIL` (does not), or `N/A` (not executable yet — see macOS gate).
4. Log the run in the footer.

## Disposition legend

- **BLOCKED (app)** — Arcade's own code prevents it (a `before-input-event` trap, `devTools:false`, or a `globalShortcut` no-op). Verify it stays blocked.
- **BLOCKED (kiosk)** — Electron's `kiosk:true` / OS presentation flag prevents it. Verify.
- **GAP** — No app or flag can prevent it at the user level. Documented; remediation noted where one exists.

## Environment capture template

```
Run date:
Engineer:
Arcade version:
Electron version:
OS (build):            e.g. Windows 11 22H2 / macOS 15.4 / Ubuntu 24.04
DE / WM (Linux):       e.g. GNOME-X11 / KDE / XFCE / Sway (Wayland)
Session type (Linux):  X11 | Wayland
```

## Windows

Code baseline: `agent/src/main/platform/windows.ts` — `before-input-event` blocks `Alt+F4, Alt+Shift+I, Control+Shift+I, Control+P, F12, F11, Escape`; every `BrowserWindow` sets `devTools:false`.

| # | Shortcut / Vector | Category | Disposition | Arcade mitigation (code ref) | Expected post-mitigation | Verification step | Test env | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|
| W1 | Alt+F4 | Close window | BLOCKED (app) | `before-input-event` + `closable:false` (`windows.ts:44-58,65-79`) | Kiosk overlay does not close; no exit. | With overlay shown, press Alt+F4. | Win 11 (build) | | |
| W2 | F12 | DevTools | BLOCKED (app) | `before-input-event` + `devTools:false` (`windows.ts:51,76`) | No DevTools window opens. | Press F12. | Win 11 | | |
| W3 | Ctrl+Shift+I | DevTools | BLOCKED (app) | `before-input-event` (`windows.ts:21,76`) | No DevTools. | Press Ctrl+Shift+I. | Win 11 | | |
| W4 | Alt+Shift+I | DevTools (Edge-style) | BLOCKED (app) | `before-input-event` (`windows.ts:20,76`) | No DevTools / feedback pane. | Press Alt+Shift+I. | Win 11 | | |
| W5 | Ctrl+P | Print | BLOCKED (app) | `before-input-event` (`windows.ts:23,76`) | No print dialog. | Press Ctrl+P. | Win 11 | | |
| W6 | F11 | Fullscreen toggle | BLOCKED (app) | `before-input-event` (`windows.ts:24,76`) | No fullscreen exit. *Observation: defensive, not in todo.* | Press F11. | Win 11 | | |
| W7 | Escape | Esc | BLOCKED (app) | `before-input-event` (`windows.ts:25,76`) | No overlay dismiss. *Observation: defensive, not in todo.* | Press Escape. | Win 11 | | |
| W8 | Ctrl+Shift+Esc | Task Manager | GAP | — | Cannot block at app level (OS-level). | Press Ctrl+Shift+Esc. | Win 11 | | Documented limitation. |
| W9 | Ctrl+Alt+Del | Secure Attention Sequence | GAP | — | Cannot block (by design). | Press Ctrl+Alt+Del. | Win 11 | | Permanent limitation. |
| W10 | Win+D | Show desktop / taskbar | GAP | — | Exposes taskbar (`electron#38020`, unresolved). | Press Win+D. | Win 11 | | Remediation: shell replacement (`Winlogon\Shell`). |
| W11 | Win+L | Lock | GAP | — | Locks session. | Press Win+L, then unlock. | Win 11 | | Document re-show-on-unlock. |
| W12 | Sticky Keys (Shift×5) | Accessibility | GAP | — | Opens Sticky Keys prompt (pivot to settings). | Press Shift 5×. | Win 11 | | Remediation: disable via Group Policy. |
| W13 | PrintScreen / Win+Shift+S | Screen capture | GAP | — | OS capture unaffected. | Press PrintScreen. | Win 11 | | OS-level. |

## macOS

> **Execution gate:** Authored against Epic 7.1 design §3 (`./specs/2026-07-18-macos-platform-design.md`). `macos.ts` is not yet implemented — **execute these rows when Epic 7.1 lands.** Until then mark Result `N/A`.

Mitigations (per 7.1 design): null application menu + `globalShortcut` no-ops + `before-input-event` + `kiosk:true` presentation flag.

| # | Shortcut / Vector | Category | Disposition | Arcade mitigation (code ref) | Expected post-mitigation | Verification step | Test env | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|
| M1 | Cmd+Q | Quit | BLOCKED (app) | `globalShortcut` no-op (`macos.ts` §3) | App does not quit. | Press Cmd+Q. | macOS (ver) | N/A | Gate: 7.1 |
| M2 | Cmd+W | Close window | BLOCKED (app) | `globalShortcut` no-op + null menu | No close. | Press Cmd+W. | macOS | N/A | Gate: 7.1 |
| M3 | Cmd+H | Hide | BLOCKED (app) | `globalShortcut` no-op + null menu | No hide. | Press Cmd+H. | macOS | N/A | Gate: 7.1 |
| M4 | Cmd+M | Minimize | BLOCKED (app) | `globalShortcut` no-op + null menu | No minimize. | Press Cmd+M. | macOS | N/A | Gate: 7.1 |
| M5 | F12 | DevTools | BLOCKED (app) | `globalShortcut` + input trap | No DevTools. | Press F12. | macOS | N/A | Gate: 7.1 |
| M6 | Cmd+Shift+I | DevTools | BLOCKED (app) | `globalShortcut` + input trap | No DevTools. | Press Cmd+Shift+I. | macOS | N/A | Gate: 7.1 |
| M7 | Alt+Shift+I | DevTools | BLOCKED (app) | `globalShortcut` + input trap | No DevTools. | Press Alt+Shift+I. | macOS | N/A | Gate: 7.1 |
| M8 | Cmd+P | Print | BLOCKED (app) | `globalShortcut` + input trap | No print dialog. | Press Cmd+P. | macOS | N/A | Gate: 7.1 |
| M9 | Cmd+Tab | App switch | BLOCKED (kiosk) | `kiosk:true` → `NSApplicationPresentationOptions` | Cannot switch apps. | Press Cmd+Tab. | macOS | N/A | Gate: 7.1 |
| M10 | Cmd+Space | Spotlight | BLOCKED (kiosk) | kiosk presentation flag | No Spotlight. | Press Cmd+Space. | macOS | N/A | Gate: 7.1 |
| M11 | Menu bar / Dock | OS chrome | BLOCKED (kiosk) | `kiosk:true` | Hidden. | Observe during session. | macOS | N/A | Gate: 7.1 |
| M12 | Cmd+Opt+Space | Finder search | GAP | — | Bypass even when Cmd+Space blocked. | Press Cmd+Opt+Space. | macOS | N/A | Blur re-assertion suggested (`./references/ARCH-02-kiosk-mode-validation.md`). |
| M13 | Cmd+Option+Esc | Force Quit | GAP | — | Cannot block (OS-level). | Press Cmd+Option+Esc. | macOS | N/A | Documented limitation. |
| M14 | Ctrl+Cmd+Power | Power dialog | GAP | — | Cannot block. | Trigger combo. | macOS | N/A | Documented limitation. |

## Linux — X11

Code baseline: `agent/src/main/platform/linux.ts` — block list mirrors Windows; `kiosk:true`. `electron#3646`: DE-dependent behavior; verify per DE.

| # | Shortcut / Vector | Category | Disposition | Arcade mitigation (code ref) | Expected post-mitigation | Verification step | Test env (DE) | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|
| L1 | Alt+F4 | Close window | BLOCKED (app) | `before-input-event` (`linux.ts:19-27,84-98`) | Overlay does not close. | Press Alt+F4. | GNOME/KDE/XFCE | | Verify per-DE. |
| L2 | F12 | DevTools | BLOCKED (app) | input trap + `devTools:false` | No DevTools. | Press F12. | per-DE | | |
| L3 | Ctrl+Shift+I | DevTools | BLOCKED (app) | input trap | No DevTools. | Press Ctrl+Shift+I. | per-DE | | |
| L4 | Alt+Shift+I | DevTools | BLOCKED (app) | input trap | No DevTools. | Press Alt+Shift+I. | per-DE | | |
| L5 | Ctrl+P | Print | BLOCKED (app) | input trap | No print dialog. | Press Ctrl+P. | per-DE | | |
| L6 | F11 | Fullscreen toggle | BLOCKED (app) | input trap | No fullscreen exit. *Observation.* | Press F11. | per-DE | | XFCE: Alt may exit fullscreen (`#3646`). |
| L7 | Escape | Esc | BLOCKED (app) | input trap | No dismiss. *Observation.* | Press Escape. | per-DE | | |
| L8 | Alt+Tab | App switch | GAP / DE-dependent | — | May be suppressed by kiosk on some WMs, not others. | Press Alt+Tab. | per-DE | | Kiosk may not suppress on all WMs (`#3646`). |
| L9 | Ctrl+Alt+Del / Ctrl+Alt+Backspace | OS | GAP | — | OS-level. | Trigger combo. | per-DE | | |
| L10 | Compositor exit (Alt exits fullscreen on XFCE) | WM-specific | GAP / DE-dependent | — | DE-dependent. | Reproduce per DE. | per-DE | | Test GNOME/KDE/XFCE/DWM. |

## Linux — Wayland

Code baseline: `agent/src/main/platform/linux.ts` `isWayland()` — applies `setKiosk` + maximize + `alwaysOnTop('screen-saver')` and logs a warning; `electron#50403` (always-on-top non-functional).

| # | Shortcut / Vector | Category | Disposition | Arcade mitigation (code ref) | Expected post-mitigation | Verification step | Test env | Result | Notes |
|---|---|---|---|---|---|---|---|---|---|
| WL1 | App-level blocks (Alt+F4, F12, Ctrl+Shift+I, Alt+Shift+I, Ctrl+P, F11, Escape) | Input traps | BLOCKED (app) | `before-input-event` (`linux.ts:84-98`) | Where input reaches renderer, no action. | Exercise each. | Wayland (compositor) | | Verify per compositor. |
| WL2 | Window / compositor switch | WM escape | GAP | — | `setAlwaysOnTop` non-functional (`#50403`). | Attempt to switch away. | Wayland | | Remediation: dedicated compositor (Cage / gnome-kiosk / ubuntu-frame). |
| WL3 | Screenshots | Capture | GAP | — | PipeWire portal prompt; fails gracefully. | Trigger server screenshot. | Wayland | | See agent-setup.md Linux note. |

## Discrepancies & observations

- **`Escape` and `F11`** appear in the code `BLOCKED_SHORTCUTS` lists (`windows.ts:24-25`, `linux.ts:24-25`) but are **not** enumerated in the Epic 7.3 todo. They are defensive (prevent fullscreen-exit / stray Esc) and harmless — recorded here as `BLOCKED (app)` observations (rows W6/W7, L6/L7).
- **`Alt+Shift+I`** is an Edge/Chromium-style shortcut, not a standard Electron DevTools binding; blocking it is defensive parity with Windows/Chromium behavior.
- **Windows Alt+F4 backstop:** `ARCH-02` recommends a `close`/`beforeunload` handler as a backstop. Current code relies on `closable:false` + input trap. If W1 ever fails, file a follow-up to add the `close` handler — out of scope for 7.3.

## Verification run log

| Run date | Engineer | Arcade ver | Electron ver | OS / DE / session | Pass | Fail | N/A |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
````

- [ ] **Step 2: Render and sanity-check the document**

Open `docs/agent-kiosk-verification.md` in a Markdown preview. Confirm: tables render, every Windows row W1–W13 / macOS M1–M14 / Linux L1–L10 / Wayland WL1–WL3 is present, macOS `Result` cells read `N/A`, and the disposition legend is present.

- [ ] **Step 3: Commit**

```bash
git add docs/agent-kiosk-verification.md
git commit -m "docs(7.3): add cross-platform kiosk hardening verification matrix"
```

---

### Task 2: Add "Kiosk Hardening & Known Limitations" to `docs/agent-setup.md`

**Files:**
- Modify: `docs/agent-setup.md` (insert a new section immediately before the `## Troubleshooting` heading)

**Interfaces:**
- Consumes: `docs/agent-kiosk-verification.md` (created in Task 1) — referenced by relative link.
- Produces: the operator-facing gap summary; linked from the matrix.

- [ ] **Step 1: Insert the gap summary section**

In `docs/agent-setup.md`, insert the following block **directly before** the existing `## Troubleshooting` line:

````markdown
## Kiosk Hardening & Known Limitations

The Arcade Agent runs as a full-screen Electron kiosk overlay (`kiosk:true`, `closable:false`, `devTools:false`) that intercepts and discards common breakout shortcuts. The full, per-platform verification matrix — every shortcut tested and its expected result — lives in [`docs/agent-kiosk-verification.md`](./agent-kiosk-verification.md).

The following vectors **cannot be blocked at the application level** and are documented as permanent limitations (not bugs):

**Windows**
- **Ctrl+Alt+Del** (Secure Attention Sequence) and **Ctrl+Shift+Esc** (Task Manager) — OS-level; no userspace app can intercept them.
- **Win+D** (show desktop / taskbar) — no supported Electron fix (`electron#38020`, unresolved). For true taskbar suppression, replace `explorer.exe` as the shell via `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\Shell` (requires deployment control of the device).
- **Win+L** (lock) — locks the session; the kiosk overlay re-shows on unlock.
- **Sticky Keys (Shift×5)** and **PrintScreen / Win+Shift+S** — OS-level accessibility/capture; disable Sticky Keys via Group Policy on managed machines.

**macOS**
- **Cmd+Option+Esc** (Force Quit) and **Ctrl+Cmd+Power** (power dialog) — OS-level, uninterceptable. (Cmd+Q, Cmd+Tab, Cmd+Space are handled by the agent / kiosk flag; see the matrix.)

**Linux — X11**
- **Alt+Tab** and compositor-specific exits — kiosk mode suppresses these inconsistently across window managers (`electron#3646`). Test per target DE (GNOME/KDE/XFCE/DWM); do not assume parity. X11 is the recommended session for client PCs.

**Linux — Wayland**
- No Electron-level API prevents switching away — `setAlwaysOnTop('screen-saver')` is non-functional on Wayland (`electron#50403`). For true lockdown, run the agent under a dedicated single-app Wayland compositor:
  ```
  cage /opt/ArcadeAgent/arcade-agent --ozone-platform-hint=auto
  ```
  (`gnome-kiosk` and `ubuntu-frame` are alternatives.) Screenshots require the PipeWire portal prompt.

````

- [ ] **Step 2: Verify the link and placement**

Confirm the section sits before `## Troubleshooting` and the relative link `./agent-kiosk-verification.md` resolves from `docs/agent-setup.md` to `docs/agent-kiosk-verification.md`.

- [ ] **Step 3: Commit**

```bash
git add docs/agent-setup.md
git commit -m "docs(agent-setup): add kiosk hardening known-limitations summary (Epic 7.3)"
```

---

### Task 3: Verification pass & TODO checklist update

**Files:**
- Modify: `docs/TODO.md` (tick Epic 7.3 checkboxes)
- Read: `docs/agent-kiosk-verification.md`, `docs/agent-setup.md`

**Interfaces:**
- Consumes: both deliverables from Tasks 1–2.
- Produces: confirmation that acceptance criteria are met; updated TODO epic status.

- [ ] **Step 1: Coverage check against the spec's acceptance criteria**

Run from repo root. Each must return a non-zero count:

```bash
grep -c "BLOCKED (app)\|BLOCKED (kiosk)\|GAP" docs/agent-kiosk-verification.md
grep -c "GAP" docs/agent-kiosk-verification.md
grep -c "agent-kiosk-verification.md" docs/agent-setup.md
```

Expected: the matrix contains all three dispositions and ≥1 `GAP` per platform; `agent-setup.md` links the matrix.

- [ ] **Step 2: Confirm no agent source changed**

```bash
git status --short
```

Expected: only `docs/agent-kiosk-verification.md` and `docs/agent-setup.md` are modified/added. No `agent/` files appear.

- [ ] **Step 3: Tick Epic 7.3 checkboxes in TODO.md**

In `docs/TODO.md`, change the three epic-level checkboxes and the gap-doc checkbox from `[ ]` to `[x]`. Use Edit with these exact old→new strings:

Old:
```
- [ ] **Windows kiosk hardening verification** (ENG-A or ENG-B):
```
New:
```
- [x] **Windows kiosk hardening verification** (ENG-A or ENG-B):
```

Old:
```
  - [ ] **Document all known gaps in `docs/agent-setup.md`**
```
New:
```
  - [x] **Document all known gaps in `docs/agent-setup.md`**
```

Old:
```
- [ ] **macOS kiosk hardening verification** (ENG-A): Cmd+Q, Cmd+Tab, Cmd+Space blocked; Force Quit (Cmd+Opt+Esc) — document if not blockable
```
New:
```
- [x] **macOS kiosk hardening verification** (ENG-A): Cmd+Q, Cmd+Tab, Cmd+Space blocked; Force Quit (Cmd+Opt+Esc) — document if not blockable
```

Old:
```
- [ ] **Linux kiosk hardening verification** (ENG-B): X11 all shortcuts blocked; Wayland fallback verified; known gaps documented
```
New:
```
- [x] **Linux kiosk hardening verification** (ENG-B): X11 all shortcuts blocked; Wayland fallback verified; known gaps documented
```

- [ ] **Step 4: Commit**

```bash
git add docs/TODO.md
git commit -m "docs(todo): mark Epic 7.3 kiosk hardening verification complete"
```
