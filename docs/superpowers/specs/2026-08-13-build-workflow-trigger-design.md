# Design: Fix false-failure "No jobs were run" emails from build.yml

Date: 2026-08-13
Status: Approved

## Problem

Every push to `main` produces a failed `build.yml` workflow run with no jobs executed, and a "Run failed: No jobs were run" notification email. The most recent example: run for commit `4d681d9` (ref `main`).

### Evidence from repository run history (GitHub API, 2026-08-13)

- The last 30 `build.yml` runs, all `event: push`, `head_branch: main`, are all `conclusion: failure`.
- The failed run's jobs list is empty (zero jobs executed).
- Runs continued failing identically **before and after** commit `287e7d3` ("ci: suppress empty workflow runs on non-tag pushes"), which added `branches-ignore: ['**']` — that run itself also failed. The `branches-ignore: ['**']` pattern, widely suggested for "tag-only" workflows, provably does **not** suppress run creation in this configuration: GitHub creates the run on every branch push and selects zero jobs, which is reported as a failed run.
- By contrast, `ci.yml` runs on the same pushes with real jobs and succeeds (green), which is why "all CI passes" while `build.yml` emails failures.

### Root cause

`build.yml` triggers on `push` with `branches-ignore: ['**']` and `tags: ['v*']`. On a push to `main`:

1. GitHub creates a workflow run for the push event.
2. The branch filter excludes `main`, so zero jobs are selected.
3. The empty run is marked `failure` ("No jobs were run") and sends the notification email.

The intended behavior was: only `v*` tag pushes and manual dispatch trigger builds. Because trigger-level exclusion still creates the run, the only reliable ways to get green runs are to either give branch pushes real jobs or remove the push trigger.

## Chosen approach

Build on every push to `main` (real jobs, green runs) plus `v*` tags, with a concurrency guard to avoid stacking full builds during rapid pushes.

```yaml
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
```

### Behavior after the change

- Every push to `main` runs the full 3-OS matrix build (real jobs → green when the build passes, which the existing manual-dispatch runs already demonstrate).
- `v*` tag pushes still trigger the build and the `release` aggregation job (`if: startsWith(github.ref, 'refs/tags/v')`).
- Manual dispatch unchanged.
- Rapid pushes: `cancel-in-progress: true` cancels the in-flight run so only the latest commit is built, minimizing wasted build minutes.

## Alternatives considered

| Option | Trade-off |
| --- | --- |
| Keep `branches-ignore: ['**']` (status quo) | Proven not to work — every push still creates a failed empty run and email. |
| Remove `push` trigger entirely (manual dispatch only) | Guaranteed zero false-failure emails, but tag pushes no longer auto-build/release; releases become manual. |
| Add `paths-ignore` for docs-only commits | Saves build minutes, but uses the same trigger-level exclusion that provably still creates failed empty runs here — would likely bring the failure emails back. |

## Changes

Single file: `.github/workflows/build.yml`.

1. In `on.push`: replace `branches-ignore: ['**']` with `branches: ['main']`.
2. Add top-level `concurrency` block (group `build-${{ github.ref }}`, `cancel-in-progress: true`).

Everything else is untouched: the matrix (windows/macos/ubuntu), `release` job, `permissions: contents: write`, `workflow_dispatch` inputs, and `ci.yml`.

## Out of scope

- Changing `ci.yml` or `security.yml` triggers.
- Path-based build skipping (deliberately excluded — see alternatives).
- The tag-push release flow (`softprops/action-gh-release` steps).

## Verification

1. Workflow YAML still parses after the edit.
2. Push a commit to `main`: the `build.yml` run must show 3 matrix jobs running (not "No jobs were run") and finish green.
3. Push a second commit while the first build is running: the first run is cancelled (concurrency) and only the latest runs.
4. No "No jobs were run" failure email arrives for either push.

## Acceptance criteria

- [ ] `build.yml` runs 3 matrix jobs and passes on a plain `main` push
- [ ] No failure notification emails on `main` pushes
- [ ] Rapid successive pushes cancel in-flight runs (only latest builds)
- [ ] `v*` tag pushes still produce release artifacts
