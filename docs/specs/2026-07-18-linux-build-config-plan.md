# Linux Build Configuration & Autostart Docs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Linux autostart reference files (`arcade-agent.desktop`, `arcade-agent.service`) and a Linux CI build workflow so the AppImage + `.deb` build is verified, completing Epic 7.2's build-config task.

**Architecture:** Pure docs + CI — no agent code changes. The `.desktop` is a reference mirror of what `agent/src/main/platform/linux.ts:enableAutoStart()` already writes at runtime; the `.service` documents both systemd user and system variants with a mutual-exclusion guard; the CI workflow mirrors `build-agent-mac.yml` because electron-builder cannot cross-compile Linux from the Windows dev host.

**Tech Stack:** YAML (GitHub Actions), INI (XDG desktop entry + systemd unit), electron-builder (AppImage/deb targets, already configured).

## Global Constraints

- `electron-builder.yml` is **unchanged** — its Linux block (`target: [AppImage, deb]`, `category: Utility`) already matches the spec verbatim.
- `agent/src/main/platform/linux.ts` is **unchanged** — `enableAutoStart()`/`disableAutoStart()` already write/delete the runtime `~/.config/autostart/arcade-agent.desktop`; existing tests cover them.
- The doc `.desktop` **must mirror exactly** what `linux.ts` writes: `Type=Application`, `Name=Arcade Agent`, `Exec=<binary>`, `X-GNOME-Autostart-enabled=true`, `X-GNOME-Autostart-Delay=5`.
- `Exec` path uses placeholder `/opt/arcade-agent/arcade-agent` with commented real paths (`.deb`: `/opt/Arcade Agent/arcade-agent` or `/usr/bin/arcade-agent`; AppImage: `/path/to/Arcade-Agent-*.AppImage`).
- `arcade-agent.service` documents **both** user + system variants with an explicit "do NOT enable both" guard.
- Linux CI workflow **mirrors `build-agent-mac.yml`**: `runs-on: ubuntu-latest`, `npm ci`, `npm run build -- --linux`, upload `dist/*.AppImage` + `dist/*.deb`.
- No AppImage/`.deb` code-signing (unsigned, consistent with macOS).
- No cross-compile from Windows — verification runs on the Linux CI runner.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `docs/autostart/arcade-agent.desktop` | Create | Canonical XDG autostart reference (mirrors `linux.ts` runtime write) |
| `docs/autostart/arcade-agent.service` | Create | systemd reference: user + system variants, mutual-exclusion guard |
| `.github/workflows/build-agent-linux.yml` | Create | Verify Linux build (AppImage + `.deb`) on `ubuntu-latest` |
| `docs/TODO.md` | Modify | Mark Epic 7.2 "Create Linux build configuration" items `[x]` |

`docs/autostart/` does not exist yet; it is created on first write.

---

### Task 1: Create `docs/autostart/arcade-agent.desktop`

**Files:**
- Create: `docs/autostart/arcade-agent.desktop`

**Interfaces:**
- Consumes: the runtime `.desktop` shape from `agent/src/main/platform/linux.ts:243-255` (must mirror it exactly).
- Produces: a committed reference file operators can read or pre-seed; also validated by `desktop-file-validate` (Linux) / the CI runner.

- [ ] **Step 1: Write the reference `.desktop` file**

Write `docs/autostart/arcade-agent.desktop` with exactly this content (header comments document real install paths; the active INI block mirrors `linux.ts`):

```ini
# Arcade Agent — XDG autostart entry (reference template)
#
# The agent writes its own copy of this file at runtime when auto-start is
# enabled from the Dashboard (Settings -> Agent -> Auto-Start). This file is the
# canonical example to read or to pre-seed manually.
#
# Set Exec to the absolute path of the installed agent binary:
#   .deb install : /opt/Arcade Agent/arcade-agent   (or /usr/bin/arcade-agent)
#   AppImage     : /path/to/Arcade-Agent-*.AppImage
[Desktop Entry]
Type=Application
Name=Arcade Agent
Exec=/opt/arcade-agent/arcade-agent
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
```

- [ ] **Step 2: Validate the desktop entry syntax**

If on a Linux machine (or the CI runner), run:

```bash
desktop-file-validate docs/autostart/arcade-agent.desktop && echo "VALID"
```

Expected: prints `VALID` with no errors. (On the Windows dev host this tool is unavailable — the CI workflow in Task 3 is the real validator; skip locally and confirm in CI.)

- [ ] **Step 3: Commit**

```bash
git add docs/autostart/arcade-agent.desktop
git commit -m "docs(agent): add Linux XDG autostart reference (arcade-agent.desktop)"
```

---

### Task 2: Create `docs/autostart/arcade-agent.service`

**Files:**
- Create: `docs/autostart/arcade-agent.service`

**Interfaces:**
- Consumes: knowledge that the agent is a GUI Electron kiosk needing a display session (from `docs/agent-setup.md` Linux section).
- Produces: a committed systemd reference documenting both variants; validated by `systemd-analyze verify` (Linux).

- [ ] **Step 1: Write the systemd reference file**

Write `docs/autostart/arcade-agent.service` with exactly this content. Both unit variants are shown as commented blocks so the operator copies the one they want; the uncommented header is the human-readable guide:

```ini
# Arcade Agent — systemd unit (reference)
#
# The agent is a GUI Electron kiosk and needs a display session.
# Choose ONE mechanism below — do NOT enable both, or the kiosk launches twice.
#
# --- Primary: systemd USER service (recommended) ---
# Install: ~/.config/systemd/user/arcade-agent.service
# Enable : systemctl --user enable --now arcade-agent.service
# Runs in the user's graphical login, so DISPLAY/WAYLAND_DISPLAY are present.
#
# [Unit]
# Description=Arcade Agent (user)
# After=graphical-session.target
#
# [Service]
# ExecStart=/opt/arcade-agent/arcade-agent
# Restart=on-failure
#
# [Install]
# WantedBy=graphical-session.target
#
# --- Secondary: systemd SYSTEM service (requires auto-login + DISPLAY) ---
# Install: /etc/systemd/system/arcade-agent.service
# Enable : sudo systemctl enable --now arcade-agent.service
# Has NO session by default; you must inject DISPLAY and use auto-login.
#
# [Unit]
# Description=Arcade Agent (system)
# After=graphical.target
#
# [Service]
# Environment=DISPLAY=:0
# ExecStart=/opt/arcade-agent/arcade-agent
# Restart=on-failure
#
# [Install]
# WantedBy=graphical.target
#
# Set ExecStart to the installed binary:
#   .deb : /opt/Arcade Agent/arcade-agent  (or /usr/bin/arcade-agent)
#   AppImage: /path/to/Arcade-Agent-*.AppImage
```

- [ ] **Step 2: Validate the unit syntax (optional, Linux only)**

To check a variant, copy the uncommented block to a temp file and run:

```bash
# example for the user variant
printf '[Unit]\nDescription=Arcade Agent (user)\nAfter=graphical-session.target\n\n[Service]\nExecStart=/opt/arcade-agent/arcade-agent\nRestart=on-failure\n\n[Install]\nWantedBy=graphical-session.target\n' > /tmp/arcade-agent.service
systemd-analyze verify /tmp/arcade-agent.service && echo "VALID"
```

Expected: prints `VALID`. (Unavailable on the Windows dev host; confirm on a Linux box or skip — no CI step runs this.)

- [ ] **Step 3: Commit**

```bash
git add docs/autostart/arcade-agent.service
git commit -m "docs(agent): add Linux systemd reference (arcade-agent.service, user + system)"
```

---

### Task 3: Create `.github/workflows/build-agent-linux.yml`

**Files:**
- Create: `.github/workflows/build-agent-linux.yml`

**Interfaces:**
- Consumes: `agent/package.json` `build` script (`tsc ... && electron-builder`) and the Linux targets already in `agent/electron-builder.yml`.
- Produces: a CI job that actually verifies `npm run build -- --linux` and uploads `dist/*.AppImage` + `dist/*.deb` (satisfies the TODO "Test build" item).

- [ ] **Step 1: Write the Linux build workflow**

Write `.github/workflows/build-agent-linux.yml` mirroring `build-agent-mac.yml`, targeting `ubuntu-latest`:

```yaml
name: Build Agent (Linux)

on:
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - 'agent/**'
      - '.github/workflows/build-agent-linux.yml'

jobs:
  build-linux:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: agent
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: "agent/package-lock.json"
      - run: npm ci
      - run: npm run build -- --linux
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: arcade-agent-linux
          path: |
            agent/dist/*.AppImage
            agent/dist/*.deb
          if-no-files-found: error
```

- [ ] **Step 2: Sanity-check YAML parses**

Run:

```bash
python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/build-agent-linux.yml')); print('YAML OK')"
```

Expected: prints `YAML OK`. (Requires PyYAML; if unavailable, the CI linter/`actionlint` will catch errors on push — still commit and verify in CI.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build-agent-linux.yml
git commit -m "ci(agent): add Linux build workflow (AppImage + deb)"
```

---

### Task 4: Mark Epic 7.2 task items complete in `docs/TODO.md`

**Files:**
- Modify: `docs/TODO.md` (Epic 7.2 block, ~lines 1444-1447)

**Interfaces:**
- Consumes: the four task items under "Task: Create Linux build configuration".
- Produces: a TODO.md reflecting the completed build-config sub-task.

- [ ] **Step 1: Update the checklist items**

In `docs/TODO.md`, find the Epic 7.2 block:

```
- [ ] **Task: Create Linux build configuration**
  - [ ] `electron-builder.yml`: `linux.target = ["AppImage", "deb"]`; `linux.category = "Utility"`
  - [ ] Test build: `npm run build -- --linux`
  - [ ] Create `docs/autostart/arcade-agent.service` (systemd) and `arcade-agent.desktop` (autostart)
```

Change each `- [ ]` to `- [x]` so it reads:

```
- [x] **Task: Create Linux build configuration**
  - [x] `electron-builder.yml`: `linux.target = ["AppImage", "deb"]`; `linux.category = "Utility"`
  - [x] Test build: `npm run build -- --linux`
  - [x] Create `docs/autostart/arcade-agent.service` (systemd) and `arcade-agent.desktop` (autostart)
```

(Note: the "Test build" item is satisfied by Task 3's CI workflow, since the Linux build cannot run on the Windows dev host.)

- [ ] **Step 2: Commit**

```bash
git add docs/TODO.md
git commit -m "docs(todo): mark Epic 7.2 Linux build configuration complete"
```

---

### Task 5: Verify end-to-end (CI)

**Files:** none (verification only)

- [ ] **Step 1: Trigger the Linux build workflow**

The workflow triggers on push to `main` under `agent/**`, or manually via `workflow_dispatch`. After pushing Tasks 1–4 (or by dispatching manually), open the run and confirm:

- `npm run build -- --linux` succeeds.
- Artifacts `arcade-agent-linux` contain `dist/*.AppImage` and `dist/*.deb`.
- `if-no-files-found: error` did not abort (i.e., both artifact types were produced).

Expected: green check on the `Build Agent (Linux)` run; both an `.AppImage` and a `.deb` are downloadable from the artifacts.

- [ ] **Step 2: Confirm no regressions elsewhere**

The new workflow only adds a Linux build; it does not alter `ci.yml`, `build-agent-mac.yml`, `electron-builder.yml`, or `linux.ts`. Existing `tests/platform/*` (including the `linux.ts` `enableAutoStart` `.desktop` write test) remain untouched and passing.

---

## Self-Review (against spec)

1. **Spec coverage:**
   - `electron-builder.yml` Linux block confirmed present / unchanged → Task 4 marks it `[x]`; no file edit needed (Global Constraint).
   - `docs/autostart/arcade-agent.desktop` reference → Task 1.
   - `docs/autostart/arcade-agent.service` (user + system, guard) → Task 2.
   - Linux build verification (`npm run build -- --linux`) → Task 3 (CI) + Task 5.
   - TODO.md items complete → Task 4.
   - All spec deliverables mapped. No gaps.

2. **Placeholder scan:** No "TBD"/"TODO"/"implement later". File contents are fully specified inline. Validation steps show exact commands + expected output. No "similar to Task N" references.

3. **Type/name consistency:** `ExecStart`/`Exec` paths use the same placeholder (`/opt/arcade-agent/arcade-agent`) and the same real-path comments across both doc files. Workflow mirrors `build-agent-mac.yml` field-for-field. TODO item text quoted verbatim from the spec. Consistent.

Plan is complete and internally consistent.
