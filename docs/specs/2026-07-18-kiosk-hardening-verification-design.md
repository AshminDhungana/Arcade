# Epic 7.3 — Cross-Platform Kiosk Hardening Verification (Design)

- **Date:** 2026-07-18
- **Epic:** 7.3 Kiosk Hardening Verification (ENG-A / ENG-B)
- **Component:** `agent/` (Electron agent kiosk overlay) + docs
- **Status:** Design approved — pending implementation plan
- **Source docs:** `docs/agent-setup.md`, `docs/references/ARCH-02-kiosk-mode-validation.md`, `docs/specs/2026-07-18-macos-platform-design.md` (Epic 7.1), `CLAUDE.md`

## Goal

Produce a **verification matrix** that confirms the agent's kiosk shortcut-hardening behaves as designed on Windows, macOS, and Linux, and a consolidated **known-limitations** summary documenting every vector that cannot be blocked at the application level. This is a *verify-and-document* epic — it does not implement new mitigations or modify agent code.

## Why a matrix (not tests)

Kiosk hardening is a security-boundary acceptance check, not a unit-testable feature. Shortcuts such as `Ctrl+Alt+Del` (Windows Secure Attention Sequence) and `Cmd+Tab` (macOS window server) are intercepted by the OS *before* Electron's JS layer receives them, so they can only be confirmed on real hardware by a human. A tabular matrix is the durable artifact: it is reviewable by ops/security non-developers and stays meaningful across OS version bumps, whereas a code test cannot reproduce a logged-in GUI session with physical keypresses.

## Scope

**In scope**
- A comprehensive breakout matrix covering all three platforms (Windows, macOS, Linux X11, Linux Wayland).
- Every shortcut enumerated in the Epic 7.3 todo **plus** every additional vector catalogued in `ARCH-02`.
- Each vector tagged with a disposition (see taxonomy below).
- Gap documentation merged into `docs/agent-setup.md`.

**Out of scope (YAGNI)**
- Implementing new mitigations (no `globalShortcut` additions, no `close`-handler backstops, no block-list extensions).
- CI / automated kiosk tests (cannot reproduce real OS input).
- Any modification to `agent/` source. If verification surfaces a *closable but currently unblocked* gap, it is filed as a follow-up ticket, not implemented here.

## Disposition taxonomy

Every matrix row carries exactly one disposition:

| Disposition | Meaning | Action in this epic |
|---|---|---|
| `BLOCKED (app)` | Arcade's own code prevents it — a `before-input-event` trap, `devTools:false`, or a `globalShortcut` no-op. | Verify it stays blocked. |
| `BLOCKED (kiosk)` | Electron's `kiosk:true` / OS presentation flag prevents it (e.g. macOS `Cmd+Tab`/`Cmd+Space` via `NSApplicationPresentationOptions`). | Verify. |
| `GAP` | No app or flag can prevent it at the user level. | Document + state remediation (or "no remediation"). |

## Current implementation baseline (for reference)

- **Windows** (`agent/src/main/platform/windows.ts`): `before-input-event` blocks `Alt+F4, Alt+Shift+I, Control+Shift+I, Control+P, F12, F11, Escape`. Every `BrowserWindow` sets `devTools:false`.
- **Linux** (`agent/src/main/platform/linux.ts`): identical block list to Windows; `isWayland()` applies `setKiosk` + maximize + `alwaysOnTop('screen-saver')` and logs a warning that the overlay is not bypass-proof on Wayland.
- **macOS** (`agent/src/main/platform/macos.ts`): **not yet implemented** (Epic 7.1, design approved). `index.ts` maps `darwin` to `./macos.js` but the file does not exist; `getPlatformService()` throws for `darwin` until 7.1 lands. The macOS matrix below is authored against the approved 7.1 design §3.

## Document structure

### `docs/agent-kiosk-verification.md` (the QA artifact)

- **Header:** purpose, how to use, disposition legend, and an **environment-capture template** (OS build, DE/WM, Electron version, Arcade version).
- **Three platform sections** (Windows / macOS / Linux), each a table with columns:
  `# · Shortcut/Vector · Category · Disposition · Arcade mitigation (code ref) · Expected post-mitigation · Verification step · Test environment · Result (PASS/FAIL/N-A) · Notes`
- **"Discrepancies & observations"** subsection — reconciles code vs todo (e.g. `Escape`/`F11` are in the block list but not in the todo; recorded as defensive `BLOCKED (app)` observations).
- **macOS section banner:** *"Defined against Epic 7.1 design §3 — execute when `macos.ts` lands."*
- **Verification run log** footer: date / engineer / OS build / Electron version / pass count, filled per executed run.

### `docs/agent-setup.md` additions

- New **"## Kiosk Hardening & Known Limitations"** section placed before *Troubleshooting*.
- Summarizes the **GAP rows only** per platform, with remediation guidance, and links to the full matrix.

## Matrix content (vectors & dispositions)

### Windows

Code: `before-input-event` blocks `Alt+F4, Alt+Shift+I, Control+Shift+I, Control+P, F12, F11, Escape`; `devTools:false` on every window.

| Vector | Disposition | Notes |
|---|---|---|
| Alt+F4 | `BLOCKED (app)` | Window is also `closable:false`. Verify no close. (`ARCH-02` recommends a `close`/`beforeunload` backstop — note as follow-up if Alt+F4 misbehaves.) |
| F12, Ctrl+Shift+I, Alt+Shift+I | `BLOCKED (app)` | No DevTools. `devTools:false` + input trap. |
| Ctrl+P | `BLOCKED (app)` | No print dialog. |
| F11, Escape | `BLOCKED (app)` | *Observation* — defensive, not in todo. |
| Ctrl+Shift+Esc (Task Manager) | `GAP` | OS-level, unblockable. |
| Ctrl+Alt+Del (SAS) | `GAP` | Secure Attention Sequence. |
| Win+D (taskbar/desktop) | `GAP` | `electron#38020` unresolved. Remediation: shell replacement (`Winlogon\Shell`). |
| Win+L (lock) | `GAP` | Document re-show-on-unlock behavior. |
| Sticky Keys (Shift×5), PrintScreen / Win+Shift+S | `GAP` | OS-level. Remediation: disable via Group Policy. |

### macOS (against Epic 7.1 design §3)

Mitigations: null application menu + `globalShortcut` no-ops + `before-input-event` + `kiosk:true` presentation flag.

| Vector | Disposition | Notes |
|---|---|---|
| Cmd+Q, Cmd+W, Cmd+H, Cmd+M | `BLOCKED (app)` | `globalShortcut` no-op (app-menu accelerators). |
| F12, Cmd+Shift+I, Alt+Shift+I, Cmd+P | `BLOCKED (app)` | `globalShortcut` + input trap. |
| Cmd+Tab, Cmd+Space, menu bar, Dock | `BLOCKED (kiosk)` | `NSApplicationPresentationOptions` via `kiosk:true` (verify). |
| Cmd+Opt+Space (Finder search) | `GAP` | Secondary bypass; blur re-assertion suggested in `ARCH-02`. |
| Cmd+Option+Esc (Force Quit), Ctrl+Cmd+Power | `GAP` | OS-level. |

### Linux — X11

Mirrors Windows block list; kiosk mode. `electron#3646` reports DE-dependent behavior.

| Vector | Disposition | Notes |
|---|---|---|
| Alt+F4, F12, Ctrl+Shift+I, Alt+Shift+I, Ctrl+P, F11, Escape | `BLOCKED (app)` | Verify **per-DE** (GNOME / KDE / XFCE / DWM). XFCE: Alt may exit fullscreen. |
| Alt+Tab, compositor-specific exits | `GAP` / DE-dependent | Per-DE test rows; kiosk mode may not suppress on all WMs. |

### Linux — Wayland

`isWayland()`: `setKiosk` + maximize + `alwaysOnTop('screen-saver')`; `electron#50403` (always-on-top non-functional).

| Vector | Disposition | Notes |
|---|---|---|
| App-level blocks (`before-input-event`) | `BLOCKED (app)` | Where input reaches the renderer — verify. |
| Window / compositor switch | `GAP` | `setAlwaysOnTop` non-functional (`#50403`). Remediation: dedicated compositor (Cage / gnome-kiosk / ubuntu-frame). |
| Screenshots | `GAP` | PipeWire portal prompt; fails gracefully. |

## macOS timing & execution model

- All three platform matrices are **authored now**; macOS rows are written against the approved 7.1 design §3.
- **Result cells:** Windows/Linux = blank template ("to be executed on target hardware"); macOS rows marked **`N/A — execute when Epic 7.1 lands`**.
- **Execution:** a human runs each step on the real café hardware/OS the deployment will use, fills `Result` + environment, and logs the run in the footer.

## Acceptance criteria (spec completeness)

The deliverable is "done" when:

1. Every Epic 7.3 todo item maps to ≥1 matrix row.
2. Every `ARCH-02` vector appears as a row.
3. Every `GAP` row carries a remediation or an explicit "no remediation" statement.
4. `docs/agent-setup.md` gap summary lists all `GAP` rows and links the matrix.
5. macOS rows carry the execution-gate banner.
6. **No `agent/` code was modified** in this epic (verify-only).

## References

- `docs/references/ARCH-02-kiosk-mode-validation.md` — shortcut-by-shortcut Electron behavior, evidence, mitigations.
- `docs/specs/2026-07-18-macos-platform-design.md` — Epic 7.1 macOS shortcut-hardening design (§3).
- `agent/src/main/platform/windows.ts`, `linux.ts`, `index.ts` — existing implementations.
- `CLAUDE.md` — agent kiosk overlay model and known-gap notes.
