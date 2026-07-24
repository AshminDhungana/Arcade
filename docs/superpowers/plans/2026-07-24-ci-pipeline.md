# CI Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create two GitHub Actions workflows (ci.yml and security.yml) that implement the CI pipeline for the Arcade project with fast-path quality checks and security scanning.

**Architecture:** Two separate workflow files for optimal PR feedback speed. ci.yml runs on every PR/push with 6 parallel jobs (lint, type-check, test). security.yml runs on PR + nightly schedule with 3 parallel jobs (bandit, pip-audit, gitleaks, npm audit). Both use built-in caching via actions/setup-python and actions/setup-node.

**Tech Stack:** GitHub Actions, Python 3.12, Node 22, ruff 0.8.0, black 24.10.0, mypy 1.13.0, pytest-cov, bandit 1.9.4, pip-audit 2.7.3, gitleaks-action v2, npm audit

## Global Constraints

- Python version: 3.12 (pinned in setup-python)
- Node version: 22 (pinned in setup-node)
- Coverage threshold: 80% (--cov-fail-under=80)
- npm audit level: high (--audit-level=high)
- Windows runner ONLY for lint-agent job
- All other jobs on ubuntu-latest
- Pip cache key: hash of backend/requirements.txt
- NPM cache keys: hash of frontend/package-lock.json and agent/package-lock.json
- Artifact retention: coverage 7 days, security reports 30 days
- Triggers: push to develop/main, PR to main (both workflows); security.yml adds daily schedule at 02:00 UTC
- Required status checks: 9 total (6 from ci.yml, 3 from security.yml)

---

### Task 1: Create `.github/workflows/ci.yml` — Fast Path Workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: Existing backend/requirements.txt, frontend/package-lock.json, agent/package-lock.json
- Produces: CI workflow with 6 parallel jobs; coverage.xml artifact named `backend-coverage`

- [ ] **Step 1: Write the complete ci.yml workflow file**

```yaml
name: CI

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [main]

jobs:
  lint-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: "backend/requirements.txt"
      - name: Install dependencies
        run: pip install -r backend/requirements.txt ruff==0.8.0 black==24.10.0
      - name: Run ruff
        run: ruff check backend/ --target-version py312
      - name: Run black check
        run: black --check backend/

  type-check-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: "backend/requirements.txt"
      - name: Install dependencies
        run: pip install -r backend/requirements.txt mypy==1.13.0
      - name: Run mypy
        run: mypy --strict backend/

  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: "backend/requirements.txt"
      - name: Install system dependencies
        run: sudo apt-get update && sudo apt-get install -y libcups2-dev
      - name: Install Python dependencies
        run: pip install -r backend/requirements.txt pytest-cov
      - name: Run tests with coverage
        run: pytest backend/ --cov=backend --cov-report=xml --cov-fail-under=80
      - name: Upload coverage artifact
        uses: actions/upload-artifact@v4
        with:
          name: backend-coverage
          path: backend/coverage.xml
          retention-days: 7

  lint-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
          cache-dependency-path: "frontend/package-lock.json"
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: Run lint
        run: cd frontend && npm run lint

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
          cache-dependency-path: "frontend/package-lock.json"
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: Run tests
        run: cd frontend && npm run test -- --run

  lint-agent:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
          cache-dependency-path: "agent/package-lock.json"
      - name: Install dependencies
        run: cd agent && npm ci
      - name: Run lint
        run: cd agent && npm run lint
```

- [ ] **Step 2: Validate YAML syntax**

Run: `yamllint .github/workflows/ci.yml` (or use GitHub's workflow validation)
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add fast-path CI workflow with lint, type-check, and test jobs"
```

---

### Task 2: Create `.github/workflows/security.yml` — Security Path Workflow

**Files:**
- Create: `.github/workflows/security.yml`

**Interfaces:**
- Consumes: backend/requirements.txt, frontend/package-lock.json, agent/package-lock.json, full git history
- Produces: Security workflow with 3 parallel jobs; artifacts: security-reports, npm-audit-reports, gitleaks-report

- [ ] **Step 1: Write the complete security.yml workflow file**

```yaml
name: Security

on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 02:00 UTC

jobs:
  security-scan-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: "backend/requirements.txt"
      - name: Install security tools
        run: pip install -r backend/requirements.txt bandit==1.9.4 pip-audit==2.7.3
      - name: Run bandit
        run: bandit -r backend/ -f json -o bandit-report.json || true
      - name: Run pip-audit
        run: pip-audit -r backend/requirements.txt -f json -o pip-audit-report.json || true
      - name: Upload security reports
        uses: actions/upload-artifact@v4
        with:
          name: security-reports
          path: |
            bandit-report.json
            pip-audit-report.json
          retention-days: 30

  dep-audit-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
      - name: Audit frontend dependencies
        run: cd frontend && npm ci && npm audit --audit-level=high --json > npm-audit-frontend.json || true
      - name: Audit agent dependencies
        run: cd agent && npm ci && npm audit --audit-level=high --json > npm-audit-agent.json || true
      - name: Upload npm audit reports
        uses: actions/upload-artifact@v4
        with:
          name: npm-audit-reports
          path: |
            npm-audit-frontend.json
            npm-audit-agent.json
          retention-days: 30

  check-secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for gitleaks
      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        with:
          args: "detect --source . --verbose --redact --report-format json --report-path gitleaks-report.json"
      - name: Upload gitleaks report
        uses: actions/upload-artifact@v4
        with:
          name: gitleaks-report
          path: gitleaks-report.json
          retention-days: 30
```

- [ ] **Step 2: Validate YAML syntax**

Run: `yamllint .github/workflows/security.yml`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/security.yml
git commit -m "ci: add security workflow with bandit, pip-audit, npm audit, and gitleaks"
```

---

### Task 3: Verify Both Workflows Run Successfully

**Files:**
- Test: `.github/workflows/ci.yml`, `.github/workflows/security.yml`

**Interfaces:**
- Consumes: Both workflow files created in Tasks 1-2
- Produces: Passing workflow runs on current main branch

- [ ] **Step 1: Push to trigger workflows**

Run: `git push origin main`
Expected: Both workflows trigger and appear in GitHub Actions tab

- [ ] **Step 2: Verify ci.yml jobs complete**

Watch: GitHub Actions → CI workflow
Expected: All 6 jobs (lint-python, type-check-python, test-backend, lint-frontend, test-frontend, lint-agent) show green checkmarks
Note: lint-agent runs on windows-latest; others on ubuntu-latest

- [ ] **Step 3: Verify security.yml jobs complete**

Watch: GitHub Actions → Security workflow
Expected: All 3 jobs (security-scan-python, dep-audit-frontend, check-secrets) show green checkmarks
Note: May show findings in artifacts (that's OK — job succeeds due to `|| true`)

- [ ] **Step 4: Verify artifacts uploaded**

Check: Each workflow run → Artifacts section
Expected:
  - CI: `backend-coverage` (7-day retention)
  - Security: `security-reports` (30-day), `npm-audit-reports` (30-day), `gitleaks-report` (30-day)

- [ ] **Step 5: Verify caching works**

Run workflows a second time (push empty commit or re-run)
Expected: "Cache hit" logs in setup-python/setup-node steps; reduced install times

---

### Task 4: Configure Branch Protection with 9 Required Status Checks

**Files:**
- None (GitHub UI configuration)

**Interfaces:**
- Consumes: Workflow job names from Tasks 1-2
- Produces: Protected main and develop branches requiring all 9 checks

- [ ] **Step 1: Configure main branch protection**

Go to: GitHub repo → Settings → Branches → Add rule for `main`
Settings:
  - Require a pull request before merging: ✓ (1 approval)
  - Require status checks to pass before merging: ✓
  - Required status checks (exact names from workflow jobs):
    - `lint-python`
    - `type-check-python`
    - `test-backend`
    - `lint-frontend`
    - `test-frontend`
    - `lint-agent`
    - `security-scan-python`
    - `dep-audit-frontend`
    - `check-secrets`
  - Require branches to be up to date before merging: ✓
  - Dismiss stale PR approvals when new commits are pushed: ✓
  - Do not allow force pushes: ✓
  - Do not allow deletions: ✓
Click: Create

- [ ] **Step 2: Configure develop branch protection**

Go to: Settings → Branches → Add rule for `develop`
Settings: Same as main (all 9 checks required)
Click: Create

- [ ] **Step 3: Verify protection works**

Create a test PR to `main`
Expected: All 9 status checks appear in PR checks section; merge button disabled until all pass

---

### Task 5: Documentation Update (Optional)

**Files:**
- Modify: `docs/developer-guide.md` (if exists)

**Interfaces:**
- Produces: Documentation for how to run CI locally and understand workflow

- [ ] **Step 1: Add CI section to developer guide** (if file exists)

Append to `docs/developer-guide.md`:
```markdown
## CI Pipeline

The project uses two GitHub Actions workflows:

### CI (ci.yml) — Runs on every PR/push
- `lint-python`: ruff + black --check
- `type-check-python`: mypy --strict
- `test-backend`: pytest with 80% coverage threshold
- `lint-frontend`: ESLint
- `test-frontend`: Vitest
- `lint-agent`: ESLint (Windows runner)

### Security (security.yml) — Runs on PR + nightly
- `security-scan-python`: bandit + pip-audit
- `dep-audit-frontend`: npm audit (high)
- `check-secrets`: gitleaks

### Local Equivalents
```bash
# Python
ruff check backend/ --target-version py312
black --check backend/
mypy --strict backend/
pytest backend/ --cov=backend --cov-fail-under=80

# Frontend
cd frontend && npm run lint
cd frontend && npm run test -- --run

# Agent
cd agent && npm run lint
```

### Artifacts
Coverage and security reports are uploaded as GitHub Actions artifacts. Download from workflow run summary.
```

---

## Acceptance Criteria Checklist

- [ ] `.github/workflows/ci.yml` created with 6 parallel jobs
- [ ] `.github/workflows/security.yml` created with 3 parallel jobs + schedule trigger
- [ ] Both workflows pass on current `main` branch
- [ ] Pip caching works (cache hit on second run)
- [ ] NPM caching works for both frontend and agent
- [ ] Coverage artifact `backend-coverage` uploads (7-day retention)
- [ ] Security artifacts upload with correct retention (30 days)
- [ ] `lint-agent` runs on `windows-latest`
- [ ] All 9 status checks configured in branch protection for `main` and `develop`
- [ ] PR to `main` shows all 9 checks; merge blocked until all pass

---

## Self-Review

**Spec coverage:** All requirements from `docs/superpowers/specs/2026-07-24-ci-pipeline-design.md` mapped to tasks:
- Task 1 → ci.yml with 6 jobs ✓
- Task 2 → security.yml with 3 jobs + schedule ✓
- Task 3 → Verification of runs, caching, artifacts ✓
- Task 4 → Branch protection with 9 checks ✓

**Placeholder scan:** No TBD, no "similar to", no vague steps — all code blocks complete, all commands exact

**Type consistency:** Job names in workflow YAML match exactly with branch protection check names in Task 4

---

Plan complete and saved to `docs/superpowers/plans/2026-07-24-ci-pipeline.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**