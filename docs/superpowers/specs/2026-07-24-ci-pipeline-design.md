# CI Pipeline Design — GitHub Actions

**Date:** 2026-07-24
**Status:** Approved — Ready for Implementation Plan
**Related:** Feature 8.1.3 in `docs/TODO.md`

---

## Overview

This design finalizes the GitHub Actions CI pipeline for the Arcade project, splitting into two workflows for optimal PR feedback speed while maintaining comprehensive security coverage.

---

## Workflow Architecture

### Two Workflow Files

| File | Purpose | Triggers |
|------|---------|----------|
| `.github/workflows/ci.yml` | Fast path: lint, type-check, test | `push` to `develop`/`main`, `pull_request` to `main` |
| `.github/workflows/security.yml` | Security path: scans, audits, secrets | Same as CI + `schedule` (daily 02:00 UTC) |

### Rationale

- **Fast path** (< 5 min): Runs on every PR/push, blocks merge
- **Security path** (2–3 min): Runs on PR + nightly, catches new CVEs proactively
- **Parallel execution**: All jobs within each workflow run in parallel
- **Separate artifacts**: Security reports retained longer for audit trail

---

## CI Workflow (`.github/workflows/ci.yml`)

### Jobs (All Parallel)

#### `lint-python`
- **Runner**: `ubuntu-latest`
- **Steps**:
  1. Checkout
  2. Setup Python 3.12 with pip cache (`cache-dependency-path: backend/requirements.txt`)
  3. Install deps + ruff + black
  4. `ruff check backend/ --target-version py312`
  5. `black --check backend/`

#### `type-check-python`
- **Runner**: `ubuntu-latest`
- **Steps**:
  1. Checkout
  2. Setup Python 3.12 with pip cache
  3. Install deps + mypy
  4. `mypy --strict backend/`

#### `test-backend`
- **Runner**: `ubuntu-latest`
- **Steps**:
  1. Checkout
  2. Setup Python 3.12 with pip cache
  4. Install system deps: `libcups2-dev`
  5. Install deps + pytest-cov
  6. `pytest backend/ --cov=backend --cov-report=xml --cov-fail-under=80`
  7. Upload `backend/coverage.xml` as artifact `backend-coverage` (7-day retention)

#### `lint-frontend`
- **Runner**: `ubuntu-latest`
- **Steps**:
  1. Checkout
  2. Setup Node 22 with npm cache (`cache-dependency-path: frontend/package-lock.json`)
  3. `cd frontend && npm ci`
  4. `cd frontend && npm run lint`

#### `test-frontend`
- **Runner**: `ubuntu-latest`
- **Steps**:
  1. Checkout
  2. Setup Node 22 with npm cache
  3. `cd frontend && npm ci`
  4. `cd frontend && npm run test -- --run`

#### `lint-agent`
- **Runner**: `windows-latest`
- **Steps**:
  1. Checkout
  2. Setup Node 22 with npm cache (`cache-dependency-path: agent/package-lock.json`)
  3. `cd agent && npm ci`
  4. `cd agent && npm run lint`

---

## Security Workflow (`.github/workflows/security.yml`)

### Triggers
```yaml
on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 02:00 UTC
```

### Jobs (All Parallel)

#### `security-scan-python`
- **Runner**: `ubuntu-latest`
- **Steps**:
  1. Checkout
  2. Setup Python 3.12 with pip cache
  3. Install deps + bandit + pip-audit
  4. `bandit -r backend/ -f json -o bandit-report.json || true`
  5. `pip-audit -r backend/requirements.txt -f json -o pip-audit-report.json || true`
  6. Upload both JSON reports as artifact `security-reports` (30-day retention)

#### `dep-audit-frontend`
- **Runner**: `ubuntu-latest`
- **Steps**:
  1. Checkout
  2. Setup Node 22 with npm cache
  3. `cd frontend && npm ci && npm audit --audit-level=high --json > npm-audit-frontend.json || true`
  4. `cd agent && npm ci && npm audit --audit-level=high --json > npm-audit-agent.json || true`
  5. Upload both JSON reports as artifact `npm-audit-reports` (30-day retention)

#### `check-secrets`
- **Runner**: `ubuntu-latest`
- **Steps**:
  1. Checkout with `fetch-depth: 0` (full history)
  2. Run `gitleaks/gitleaks-action@v2`:
     ```
     args: "detect --source . --verbose --redact --report-format json --report-path gitleaks-report.json"
     ```
  3. Upload `gitleaks-report.json` as artifact `gitleaks-report` (30-day retention)

---

## Caching Strategy

| Language | Tool | Cache Key | Invalidation |
|----------|------|-----------|--------------|
| Python | `actions/setup-python@v5` with `cache: pip` | Hash of `backend/requirements.txt` | On requirements.txt change |
| Node.js (frontend) | `actions/setup-node@v4` with `cache: npm` | Hash of `frontend/package-lock.json` | On package-lock.json change |
| Node.js (agent) | `actions/setup-node@v4` with `cache: npm` | Hash of `agent/package-lock.json` | On package-lock.json change |

---

## Artifacts Summary

| Artifact | Source | Retention | Use Case |
|----------|--------|-----------|----------|
| `backend-coverage` | `backend/coverage.xml` | 7 days | Coverage enforcement, optional Codecov upload |
| `security-reports` | `bandit-report.json`, `pip-audit-report.json` | 30 days | Security review, CVE tracking |
| `npm-audit-reports` | `npm-audit-frontend.json`, `npm-audit-agent.json` | 30 days | Dependency audit review |
| `gitleaks-report` | `gitleaks-report.json` | 30 days | Secret scan audit trail |

---

## Branch Protection Configuration

### Required Status Checks (9 total)
| Check | Workflow | Job |
|-------|----------|-----|
| `lint-python` | ci.yml | lint-python |
| `type-check-python` | ci.yml | type-check-python |
| `test-backend` | ci.yml | test-backend |
| `lint-frontend` | ci.yml | lint-frontend |
| `test-frontend` | ci.yml | test-frontend |
| `lint-agent` | ci.yml | lint-agent |
| `security-scan-python` | security.yml | security-scan-python |
| `dep-audit-frontend` | security.yml | dep-audit-frontend |
| `check-secrets` | security.yml | check-secrets |

### Rules (main & develop branches)
- Require PR reviews: 1 approval
- Require status checks: All 9 checks must pass
- Require branches up to date before merging: Yes
- Dismiss stale reviews on new commits: Yes
- Restrict force pushes: Yes
- Restrict deletions: Yes

---

## Implementation Notes

### Python Version
- Uses **Python 3.12** (matches `backend/requirements.txt` validated versions)
- `ruff==0.8.0`, `black==24.10.0`, `mypy==1.13.0` pinned to match dev dependencies

### Node Version
- Uses **Node 22** (matches `engines` field in package.json if present, otherwise latest LTS)

### Windows Runner
- Only `lint-agent` uses `windows-latest` (native Electron/Sharp/better-sqlite3 compilation)
- All other jobs use `ubuntu-latest` for speed

### System Dependencies
- `libcups2-dev` installed in `test-backend` for `python-escpos` (thermal printing)

### Security Tool Versions
- `bandit==1.9.4`, `pip-audit==2.7.3` (from `requirements-dev.txt`)
- `gitleaks/gitleaks-action@v2` (latest stable)
- `npm audit --audit-level=high` (built-in)

---

## Future Enhancements (Out of Scope)

- **Codecov integration**: Add upload step in `test-backend` if desired
- **Dependency review action**: GitHub's native `dependency-review` for PRs
- **SAST**: Add CodeQL analysis for deeper static analysis
- **Container scanning**: If Docker images are added later

---

## Acceptance Criteria

- [ ] Both workflow files created and committed
- [ ] All 9 status checks appear on PRs to `main`
- [ ] Branch protection rules updated with all 9 checks
- [ ] Pipelines pass on current `main` branch
- [ ] Coverage artifact uploads correctly
- [ ] Security artifacts upload with findings (if any)
- [ ] Windows `lint-agent` job completes successfully
- [ ] Pip/npm caching reduces subsequent run times by > 50%
