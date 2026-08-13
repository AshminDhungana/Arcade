# Build Workflow Trigger Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the false-failure "No jobs were run" emails from `build.yml` by building on every push to `main` (real jobs) plus `v*` tags, with a concurrency guard.

**Architecture:** Single-file edit to `.github/workflows/build.yml`: swap the `branches-ignore: ['**']` trigger (proven not to suppress run creation — it leaves zero selected jobs and marks the run failed) for `branches: ['main']`, and add a top-level `concurrency` block so rapid pushes cancel in-flight builds. No path filters (they use the same trigger-level exclusion that provably still creates failed empty runs).

**Tech Stack:** GitHub Actions (YAML workflow), git.

## Global Constraints

- Only file changed: `.github/workflows/build.yml` (from the spec: `on.push` swap + top-level `concurrency`).
- Do NOT touch `ci.yml`, `security.yml`, or any job body/step inside `build.yml`.
- Keep `tags: ['v*']`, `workflow_dispatch` + its `version` input, matrix, `release` job, and `permissions: contents: write` exactly as-is.
- Do NOT add `paths`/`paths-ignore` filters (spec: they risk recreating the failed-empty-run emails).
- Working tree must stay clean between commits; repository uses pre-commit hooks (ruff, mypy, bandit, yaml check).

---

### Task 1: Rewrite the trigger and add concurrency guard

**Files:**
- Modify: `.github/workflows/build.yml:3-12` (the `on:` block) and insert a `concurrency` block after it, before `permissions:`
- Verify: `git grep` against spec (below)

**Interfaces:**
- Consumes: spec at `docs/superpowers/specs/2026-08-13-build-workflow-trigger-design.md` (Approved)
- Produces: a workflow that runs 3 matrix jobs on every `main` push, on `v*` tag pushes, and on manual dispatch; cancels in-flight runs on rapid pushes

- [ ] **Step 1: Read the current `on:` block**

Read `.github/workflows/build.yml` lines 1-16. Confirm the file currently contains:

```yaml
on:
  push:
    branches-ignore: ['**']
    tags: ['v*']
  workflow_dispatch:
    inputs:
      version:
        description: 'Version override (e.g., 1.0.0)'
        required: false
        type: string

permissions:
  contents: write
```

- [ ] **Step 2: Apply the edit**

Replace `branches-ignore: ['**']` with `branches: ['main']` and add the concurrency block, so the top of the file reads exactly:

```yaml
name: Build All Platforms

on:
  push:
    branches: ['main']
    tags: ['v*']
  workflow_dispatch:
    inputs:
      version:
        description: 'Version override (e.g., 1.0.0)'
        required: false
        type: string

concurrency:
  group: build-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: write
```

Using an edit tool: replace `    branches-ignore: ['**']` with `    branches: ['main']`, then replace the block

```yaml
        type: string

permissions:
```

with

```yaml
        type: string

concurrency:
  group: build-${{ github.ref }}
  cancel-in-progress: true

permissions:
```

- [ ] **Step 3: Verify the YAML still parses**

Run the repo's Yamllint/pre-commit hooks on the changed file:

```bash
git diff .github/workflows/build.yml
```

Expected: exactly two hunks — the `branches-ignore` → `branches` line change, and the inserted `concurrency` block. No other lines changed. The changed file must have no syntax errors (the block is plain YAML mapping + flow lists; valid).

Also run the yaml pre-commit check (installed in repo pre-commit config):

```bash
pre-commit run --files .github/workflows/build.yml
```

Expected: `check yaml` passes (all other hooks report `(no files to check)` or pass).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: build on main pushes and cancel stale in-flight builds"
```

Expected: pre-commit hooks pass (ruff/mypy/bandit report no files to check; yaml check passes), commit succeeds.

- [ ] **Step 5: Push and verify run creation**

```bash
git push origin main
```

Then verify via the GitHub API (no auth needed; repo is public):

```bash
curl -s "https://api.github.com/repos/AshminDhungana/Arcade/actions/runs?per_page=5&event=push" | grep -E '"name"|"head_sha"|"conclusion"|"event"' | head -20
```

Expected: the newest `build.yml` run (head_sha = the just-pushed commit) shows 3 jobs queued/running (NOT "No jobs were run"). Acceptance: the run concludes success, and no "Run failed: No jobs were run" email arrives. Optionally watch jobs:

```bash
curl -s "https://api.github.com/repos/AshminDhungana/Arcade/actions/runs/<run_id>/jobs" | grep '"conclusion"'
```

Expected eventually: three `"conclusion": "success"` entries.

- [ ] **Step 6: Verify concurrency cancel on rapid pushes**

Push a second commit within a few minutes of the first (while its build still runs):

```bash
git commit --allow-empty -m "ci: exercise concurrency cancellation" && git push origin main
```

Expected: the first run is cancelled (its conclusion becomes `cancelled`), the new run takes over with 3 jobs.

## Acceptance Criteria (from spec)

- [ ] `build.yml` runs 3 matrix jobs and passes on a plain `main` push
- [ ] No failure notification emails on `main` pushes
- [ ] Rapid successive pushes cancel in-flight runs (only latest builds)
- [ ] `v*` tag pushes still produce release artifacts (untouched trigger path — verify on next tag push)
