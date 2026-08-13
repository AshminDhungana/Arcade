# Gitleaks Action v2 Pin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the failing `check-secrets` CI job pass by pinning `gitleaks/gitleaks-action` from v3 to v2.

**Architecture:** Single-line change in `.github/workflows/security.yml`. v2 of the action supports the existing `config`/`args` inputs and requires no license key. All other job steps (checkout with `fetch-depth: 0`, config, args, artifact upload) remain unchanged.

**Tech Stack:** GitHub Actions, gitleaks-action v2 (moving tag, currently v2.3.9).

## Global Constraints

- Only `.github/workflows/security.yml` may be modified — no changes to `.gitleaks.toml`, other workflows, or any source code.
- Must use `gitleaks/gitleaks-action@v2` exactly (v3 requires a license and drops the `config`/`args` inputs in use).
- Keep existing inputs: `config: .gitleaks.toml`, `args: "--verbose --redact --report-format json --report-path gitleaks-report.json"`.
- Pre-commit hooks run on every commit (ruff, mypy, bandit, check yaml, end-of-file, trailing whitespace, large files, private keys) — the `check yaml` hook will validate the workflow file.

---

### Task 1: Pin gitleaks action to v2 in security.yml

**Files:**
- Modify: `.github/workflows/security.yml:66`

**Interfaces:**
- Consumes: nothing (no earlier tasks)
- Produces: a `check-secrets` job that runs `gitleaks detect` under v2 and uploads `gitleaks-report.json`; verified by push-triggered CI on GitHub

- [ ] **Step 1: Make the edit**

In `.github/workflows/security.yml`, change line 66:

```diff
-      - uses: gitleaks/gitleaks-action@v3
+      - uses: gitleaks/gitleaks-action@v2
```

Do not touch any other line. The surrounding job must remain:

```yaml
  check-secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0  # Full history for gitleaks
      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        with:
          config: .gitleaks.toml
          args: "--verbose --redact --report-format json --report-path gitleaks-report.json"
      - name: Upload gitleaks report
        uses: actions/upload-artifact@v4
        with:
          name: gitleaks-report
          path: gitleaks-report.json
          retention-days: 30
```

- [ ] **Step 2: Verify the YAML still parses**

Run the repo's yaml check hook:

```bash
pre-commit run check-yaml --files .github/workflows/security.yml
```

Expected: PASS (`check yaml` hook passes for `.github/workflows/security.yml`).

Sanity check the edit:

```bash
git diff .github/workflows/security.yml
```

Expected: exactly one line changed (`@v3` → `@v2`); no other edits.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/security.yml
git commit -m "ci: pin gitleaks-action to v2 to fix check-secrets job"
```

Expected: commit succeeds with all pre-commit hooks passing.

- [ ] **Step 4: Push and confirm CI passes**

```bash
git push origin develop
```

Expected: the `Security` workflow runs. In the `check-secrets` job log:
- NO `Warning: Unexpected input(s) 'config', 'args'` for the gitleaks step
- NO `🛑 missing gitleaks license` error
- Job completes successfully and the `gitleaks-report` artifact is uploaded

Note: if CI shows a green run, the job is fixed. Push only predicts; the GitHub run is the authoritative verification and may take a few minutes to appear.
