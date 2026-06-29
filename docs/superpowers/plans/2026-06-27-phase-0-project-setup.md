# Phase 0: Project Setup & Tooling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a fully operational monorepo — folder structure, Python + Node toolchains, linters, pre-commit hooks, CI skeleton, Makefile, and docs scaffolding — so any engineer can clone and have a running dev environment within 30 minutes.

**Architecture:** Single git repo (already initialised at `AshminDhungana/Arcade`). Four components scaffolded per `docs/Folder_Structure.md`: `backend/` (Python/FastAPI, venv at `backend/venv`), `frontend/` (React+Vite+TS), `agent/` (Electron+TS), and root `launcher.py` / `alembic/` / `tools/keygen/`. Linting via Ruff+Black+Mypy (Python) and ESLint+Prettier (TS), wired through `pre-commit`. CI on GitHub Actions runs on every PR.

**Tech Stack:** Python 3.13.12, Node 24.18.0, FastAPI, SQLAlchemy[asyncio]+aiosqlite, React+Vite+Tailwind, Electron, Ruff/Black/Mypy/ESLint/Prettier, pre-commit, GitHub Actions.

---

## Environment reconciliation (deviations from TODO.md — read before executing)

TODO.md Feature 0.1.2/0.1.3 pins older toolchain versions. This plan **deliberately diverges** in three places, because the architecture-validation spikes (ARCH-01/03/05/06) already *proved* the newer stack works on this machine. Downgrading would invalidate proven validation work.

| Item | TODO.md says | This machine / validated | Plan decision |
|---|---|---|---|
| Python | 3.12.x | **3.13.12** | Use 3.13.12 (all spikes passed). |
| Node | 20 LTS | **v24.18.0** | Use 24.18.0 (Vite + Electron both support it). |
| Git remote | `neurotech-biratnagar/arcade` | **`AshminDhungana/Arcade`** | Use the real remote. |
| `fastapi` | 0.111.0 | **0.138.1** (ARCH-06) | Keep validated pin. |
| `sqlalchemy[asyncio]` | 2.0.30 | **2.0.51** (ARCH-01) | Keep validated pin. |
| `aiosqlite` | 0.20.0 | **0.22.1** (ARCH-01) | Keep validated pin. |
| `uvicorn[standard]` | 0.30.0 | **0.49.0** (ARCH-06) | Keep validated pin. |
| `httpx` | 0.27.0 | **0.28.1** (ARCH-05/06) | Keep validated pin. |
| `PyNaCl` | 1.5.0 | **1.6.2** (ARCH-05) | Keep validated pin. |
| `py-machineid` | 0.6.0 | **1.0.0** (ARCH-05) | Keep validated pin. |
| `pytest` | 8.2.0 | **9.1.1** (spikes) | Keep validated pin. |
| `pytest-asyncio` | 0.23.7 | **1.4.0** (ARCH-06) | Keep validated pin. |

The remaining deps (alembic, pydantic, argon2-cffi, python-jose, apscheduler, cryptography, pyinstaller, tinytuya, python-escpos, and the dev toolchain) are **new** to this repo and pinned to recent-stable versions below. Task 2's install step is the gate: if `pip` reports a hard conflict for any new pin, bump *that pin only* to the version `pip` resolves, and record the final pin in the requirements file. Do not downgrade the 9 validated pins above.

**Cross-platform note:** This is a Windows host (Git Bash). `make` is not guaranteed on Windows — Task 8 documents the underlying commands alongside each Makefile target. `better-sqlite3` (Task 6) is a native module; if prebuilds are missing for the Node 24 ABI, `npm install` will attempt a source build requiring the windows-build-tools / MSVC toolchain — this is flagged as a risk.

**Existing artifacts to preserve:** `backend/arch01_app.py`, `backend/arch01_stress_test.py`, `backend/tests/validation_tasks/` (ARCH-01/03/05/06 spikes), `backend/requirements.txt`, `backend/venv/`, `LICENSE`, `README.md`, `.gitignore`, `CLAUDE.md`, and all of `docs/`. Do not delete or move these.

---

## File Structure (what this plan creates/changes)

| Path | Created by Task | Responsibility |
|---|---|---|
| `backend/{api/{routers},services,repositories,models,schemas,licensing,core,scripts}/.gitkeep` | Task 1 | Empty module dirs (filled in Phase 1+) |
| `frontend/src/{pages,components,hooks,api,store,utils}/.gitkeep` | Task 1 | Empty frontend dirs |
| `agent/src/main/{platform,storage,ipc,ws,health,tray}/.gitkeep`, `agent/src/renderer/.gitkeep` | Task 1 | Empty agent dirs |
| `alembic/{versions}/.gitkeep` | Task 1 | Empty migration dirs |
| `.gitignore` (augment) | Task 1 | Ensure security-critical entries present |
| `backend/requirements.txt` (extend) | Task 2 | Production Python deps |
| `backend/requirements-dev.txt` | Task 2 | Dev Python deps |
| `pyproject.toml` | Task 3 | Ruff + Black + Mypy config |
| `.pre-commit-config.yaml` | Task 4 | pre-commit hooks (Python + TS) |
| `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/index.html`, `frontend/src/main.tsx` | Task 5 | Vite React-TS scaffold |
| `agent/package.json`, `agent/tsconfig.json`, `agent/tsconfig.main.json`, `agent/electron-builder.yml`, `agent/src/main/index.ts` | Task 6 | Electron scaffold |
| `frontend/.eslintrc.json`, `agent/.eslintrc.json`, `.prettierrc` | Task 7 | TS linting |
| `Makefile` | Task 8 | Common dev commands |
| `.github/workflows/ci.yml` | Task 9 | CI pipeline |
| `.github/pull_request_template.md` | Task 9 | PR template |
| `docs/CONTRIBUTING.md`, placeholder docs | Task 10 | Docs scaffolding |
| `docs/superpowers/plans/2026-06-27-phase-0-project-setup.md` | (this file) | The plan |

---

## Task 1: Folder Structure Scaffold (Feature 0.1.1)

**Files:**
- Create: empty dirs with `.gitkeep` per `docs/Folder_Structure.md`
- Modify: `.gitignore` (audit + augment security entries)

- [ ] **Step 1: Create backend module directories with `.gitkeep`**

Run (Git Bash, from repo root):
```bash
mkdir -p backend/api/routers backend/services backend/repositories backend/models backend/schemas backend/licensing backend/core backend/scripts
for d in backend/api/routers backend/services backend/repositories backend/models backend/schemas backend/licensing backend/core backend/scripts; do touch "$d/.gitkeep"; done
```
Expected: eight `.gitkeep` files created; `find backend -name .gitkeep` lists them.

- [ ] **Step 2: Create frontend source directories with `.gitkeep`**

```bash
mkdir -p frontend/src/pages frontend/src/components frontend/src/hooks frontend/src/api frontend/src/store frontend/src/utils
for d in frontend/src/pages frontend/src/components frontend/src/hooks frontend/src/api frontend/src/store frontend/src/utils; do touch "$d/.gitkeep"; done
```
Expected: six `.gitkeep` files.

- [ ] **Step 3: Create agent source directories with `.gitkeep`**

```bash
mkdir -p agent/src/main/platform agent/src/main/storage agent/src/main/ipc agent/src/main/ws agent/src/main/health agent/src/main/tray agent/src/renderer
for d in agent/src/main/platform agent/src/main/storage agent/src/main/ipc agent/src/main/ws agent/src/main/health agent/src/main/tray agent/src/renderer; do touch "$d/.gitkeep"; done
```
Expected: seven `.gitkeep` files.

- [ ] **Step 4: Create alembic directories with `.gitkeep`**

```bash
mkdir -p alembic/versions
touch alembic/versions/.gitkeep
```
Expected: `alembic/versions/.gitkeep` exists.

- [ ] **Step 5: Verify `.gitignore` covers security-critical patterns**

Read `.gitignore`. Confirm these entries exist (add any missing). These entries are **mandatory** (R-05 mitigation):

```gitignore
# Security-critical — NEVER commit
tools/keygen/private_key.pem
*.pem
*.key
license.key
arcade.config.json
agent/agent.config.json

# Runtime databases
*.db
*.db-shm
*.db-wal
backups/

# Node
node_modules/
frontend/dist/
agent/dist/
.cache/

# OS / editor
.DS_Store
Thumbs.db
.idea/
.vscode/
*.swp

# Build artifacts
build/
*.spec
_MEI*/
```
Expected: `git check-ignore tools/keygen/private_key.pem license.key arcade.config.json agent/agent.config.json` prints all four paths (each is ignored).

- [ ] **Step 6: Verify no tracked secrets and commit**

```bash
git status --short
git add .gitignore backend frontend agent alembic
git commit -m "chore(phase0): scaffold folder structure per Folder_Structure.md"
```
Expected: commit succeeds; `git log --all --full-history -- '**/*.pem'` returns empty.

---

## Task 2: Python Requirements (Feature 0.1.2 part 1)

**Files:**
- Modify: `backend/requirements.txt` (extend, keep validated pins)
- Create: `backend/requirements-dev.txt`

- [ ] **Step 1: Extend `backend/requirements.txt` with missing production deps**

The file already contains the 9 validated pins (see reconciliation table). Append the missing production deps so the final file is exactly:

```text
# === Validated by ARCH-01/03/05/06 spikes — do NOT downgrade ===
fastapi==0.138.1
sqlalchemy[asyncio]==2.0.51
aiosqlite==0.22.1
uvicorn[standard]==0.49.0
httpx==0.28.1
PyNaCl==1.6.2
py-machineid==1.0.0
pytest==9.1.1
pytest-asyncio==1.4.0

# === Added in Phase 0 (production) ===
pydantic==2.10.4
alembic==1.14.0
argon2-cffi==23.1.0
python-jose[cryptography]==3.4.0
apscheduler==3.11.0
cryptography==44.0.0
pyinstaller==6.12.0
tinytuya==1.17.0
python-escpos==3.1.0
```

- [ ] **Step 2: Create `backend/requirements-dev.txt`**

```text
# Dev / lint / test toolchain (Phase 0)
pytest==9.1.1
pytest-asyncio==1.4.0
pytest-cov==6.0.0
httpx==0.28.1
ruff==0.8.0
mypy==1.13.0
black==24.10.0
pre-commit==4.0.1
bandit==1.7.11
pip-audit==2.7.3
locust==2.32.0
faker==33.0.0
```
(`pytest`, `pytest-asyncio`, `httpx` are duplicated intentionally so dev-only installs are self-contained.)

- [ ] **Step 3: Install into the existing `backend/venv` and resolve any conflicts**

```bash
cd backend
# Use the existing venv (gitignored at ./backend/venv). Activate it:
# Git Bash:  source venv/Scripts/activate
# If venv is missing: python -m venv venv && source venv/Scripts/activate
source venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
```
Expected: install completes. **If a hard conflict is reported for any *new* (non-validated) pin:** bump only that pin to the version `pip` resolves, edit the requirements file, re-run. Do **not** downgrade the 9 validated pins. Record any change in the commit message.

- [ ] **Step 4: Verify imports succeed**

```bash
python -c "import fastapi, sqlalchemy, aiosqlite, nacl, jose, argon2, apscheduler, alembic, pydantic, cryptography; print('imports OK')"
```
Expected: prints `imports OK`. If `tinytuya` or `python-escpos` fail to import on Windows (optional/deferred features), that's acceptable for Phase 0 — note it but do not block; they are not needed until Phase 5.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/requirements-dev.txt
git commit -m "deps(phase0): extend backend requirements (keep validated pins, add production deps)"
```

---

## Task 3: pyproject.toml — Ruff, Black, Mypy (Feature 0.1.2 part 2)

**Files:**
- Create: `pyproject.toml` (repo root)

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[tool.ruff]
line-length = 88
target-version = "py313"
extend-exclude = ["backend/tests/validation_tasks", "backend/venv"]

[tool.ruff.lint]
# E/F pyflakes+pycodestyle, I isort, UP pyupgrade, B bugbear, S bandit
select = ["E", "F", "I", "UP", "B", "S"]

[tool.ruff.lint.per-file-ignores]
# Validation spikes and tests may use asserts, large literals, etc.
"backend/tests/**" = ["S101", "S106"]
"backend/tests/validation_tasks/**" = ["S101", "S106", "E501", "S311"]

[tool.black]
line-length = 88
target-version = ["py313"]
extend-exclude = "backend/(venv|tests/validation_tasks)"

[tool.mypy]
python_version = "3.13"
strict = true
exclude = "(venv|tests/validation_tasks|arch01_)"
# Phase 0 has no typed source yet; allow untyped third-party stubs.
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["backend/tests"]
```

- [ ] **Step 2: Verify linters run clean on the current tree**

```bash
ruff check backend/
black --check backend/
```
Expected: ruff reports only within `backend/tests/validation_tasks` (excluded) or zero issues; black reports no reformatting needed outside excluded dirs. (Spikes are excluded — they are frozen validation artifacts.)

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore(phase0): pyproject.toml — ruff/black/mypy config"
```

---

## Task 4: pre-commit Configuration (Feature 0.1.2 part 3 + shared)

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Create `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.10
        args: [--strict, --ignore-missing-imports]
        exclude: "tests/|venv/|validation_tasks/|arch01_"

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.11
    hooks:
      - id: bandit
        args: [-r, backend/]
        exclude: "tests/|venv/"

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-yaml
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-added-large-files
        args: ["--maxkb=1024"]
      - id: detect-private-key   # R-05 mitigation: blocks any PEM/private key
```

- [ ] **Step 2: Install the git hook**

```bash
pre-commit install
```
Expected: `pre-commit installed at .git/hooks/pre-commit`.

- [ ] **Step 3: Verify hooks fire and pass on the skeleton**

```bash
pre-commit run --all-files
```
Expected: all hooks pass (failures, if any, should be only cosmetic fixes in non-excluded files — apply them with `ruff check --fix` / `ruff format`). The `detect-private-key` hook must pass (no keys in tree).

- [ ] **Step 4: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "chore(phase0): pre-commit hooks (ruff, black, mypy, bandit, detect-private-key)"
```

---

## Task 5: Frontend Scaffold — Vite + React + TS + Tailwind (Feature 0.1.3 part 1)

**Files:**
- Create: `frontend/package.json`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`

- [ ] **Step 1: Scaffold the Vite React-TS app inside `frontend/`**

```bash
cd frontend
npm create vite@latest . -- --template react-ts
# If prompted about non-empty dir (the .gitkeep files), choose "Ignore files and continue".
```
Expected: `package.json`, `index.html`, `vite.config.ts`, `tsconfig.json`, `src/main.tsx`, `src/App.tsx`, `src/index.css` created.

- [ ] **Step 2: Install runtime + dev dependencies**

```bash
# Runtime
npm install @tanstack/react-query react-router-dom zustand recharts lucide-react
# Tailwind
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
# Test
npm install -D vitest @testing-library/react @testing-library/user-event jsdom @vitejs/plugin-react
```
Expected: `node_modules/` created (gitignored); `tailwind.config.js` + `postcss.config.js` created.

- [ ] **Step 3: Configure Tailwind**

Replace `frontend/tailwind.config.js` content with:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
```

Replace `frontend/src/index.css` content with:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 4: Configure `vite.config.ts` (API + WS proxy)**

```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": "/src" },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [],
  },
});
```

- [ ] **Step 5: Configure `tsconfig.json` path alias `@/` → `src/`**

Add to `compilerOptions` in `frontend/tsconfig.json`:
```json
"baseUrl": ".",
"paths": { "@/*": ["src/*"] }
```
Ensure `"strict": true` is set.

- [ ] **Step 6: Verify the scaffold runs**

```bash
npm run dev   # starts Vite dev server — Ctrl-C once confirmed
npm run build # produces frontend/dist/
```
Expected: dev server starts on the Vite port; `npm run build` produces `frontend/dist/`.

- [ ] **Step 7: Add a vitest smoke test**

Create `frontend/src/__tests__/smoke.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";

describe("smoke", () => {
  it("vitest runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```
Run:
```bash
npm test -- --run
```
Expected: 1 test passes (zero failures). Remove the `.gitkeep` from `frontend/src/pages` etc. only when real files land; keep them for now.

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat(phase0): scaffold frontend (Vite + React-TS + Tailwind + vitest)"
```

---

## Task 6: Electron Agent Scaffold (Feature 0.1.3 part 2)

**Files:**
- Create: `agent/package.json`, `agent/tsconfig.json`, `agent/tsconfig.main.json`, `agent/electron-builder.yml`, `agent/src/main/index.ts`

- [ ] **Step 1: Initialise the agent package**

```bash
cd agent
npm init -y
```

Replace `agent/package.json` with:
```json
{
  "name": "arcade-agent",
  "version": "0.0.0",
  "description": "Arcade kiosk agent (Electron)",
  "main": "dist/main/index.js",
  "scripts": {
    "build": "tsc -p tsconfig.main.json && electron-builder",
    "start": "tsc -p tsconfig.main.json && electron .",
    "lint": "eslint src --ext .ts"
  },
  "devDependencies": {},
  "dependencies": {}
}
```

- [ ] **Step 2: Install dev + runtime deps**

```bash
npm install -D electron electron-builder typescript ts-node
npm install better-sqlite3 systeminformation sharp
```
**⚠ Risk:** `better-sqlite3` is a native module. If `npm install` fails to fetch a prebuild for the Node 24 ABI, it will attempt a source build (needs MSVC / `windows-build-tools`). If the source build fails, install build tooling (`npm config set msvs_version 2022` after installing VS Build Tools) or temporarily use Node 20 LTS via nvm. Record the outcome in the commit message.

Expected: `node_modules/` created.

- [ ] **Step 3: Create `agent/tsconfig.main.json` (CommonJS, main process)**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "CommonJS",
    "moduleResolution": "node",
    "outDir": "dist/main",
    "rootDir": "src/main",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true
  },
  "include": ["src/main/**/*.ts"]
}
```

- [ ] **Step 4: Create `agent/tsconfig.json` (base/shared)**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  },
  "include": ["src"]
}
```

- [ ] **Step 5: Create the stub main process `agent/src/main/index.ts`**

```ts
import { app, BrowserWindow } from "electron";
import * as path from "path";

function createWindow(): void {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    title: "Arcade Agent",
  });
  win.loadURL("data:text/html,<h1>Arcade Agent (scaffold)</h1>");
}

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
```

- [ ] **Step 6: Create `agent/electron-builder.yml`**

```yaml
appId: com.neurotech.arcade.agent
productName: Arcade Agent
copyright: Neurotech Biratnagar
directories:
  output: dist
files:
  - "dist/main/**/*"
  - "package.json"
win:
  target:
    - nsis
mac:
  target:
    - dmg
    - zip
linux:
  target:
    - AppImage
    - deb
  category: Utility
nsis:
  oneClick: false
```

- [ ] **Step 7: Verify the agent builds and opens a window**

```bash
npm run build   # tsc compiles to dist/main/; electron-builder packages (may be slow first run)
```
Expected: `dist/main/index.js` produced; electron-builder generates platform output under `agent/dist/`. (Opening the window itself is verified manually later; for Phase 0 the compile + build succeeding is the gate.)

- [ ] **Step 8: Commit**

```bash
git add agent/
git commit -m "feat(phase0): scaffold electron agent (main process + electron-builder)"
```

---

## Task 7: TypeScript Linting — ESLint + Prettier (Feature 0.1.3 part 3)

**Files:**
- Create: `frontend/.eslintrc.json`, `agent/.eslintrc.json`, `.prettierrc`

- [ ] **Step 1: Install ESLint stack in both projects**

```bash
cd frontend
npm install -D eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser eslint-plugin-react-hooks prettier eslint-config-prettier
cd ../agent
npm install -D eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser prettier eslint-config-prettier
cd ..
```

- [ ] **Step 2: Create `frontend/.eslintrc.json`**

```json
{
  "root": true,
  "parser": "@typescript-eslint/parser",
  "parserOptions": { "ecmaVersion": 2022, "sourceType": "module", "ecmaFeatures": { "jsx": true } },
  "plugins": ["@typescript-eslint", "react-hooks"],
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "prettier"
  ],
  "rules": {
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn",
    "@typescript-eslint/no-unused-vars": ["warn", { "argsIgnorePattern": "^_" }]
  }
}
```

- [ ] **Step 3: Create `agent/.eslintrc.json`**

```json
{
  "root": true,
  "parser": "@typescript-eslint/parser",
  "parserOptions": { "ecmaVersion": 2022, "sourceType": "module" },
  "plugins": ["@typescript-eslint"],
  "extends": ["eslint:recommended", "plugin:@typescript-eslint/recommended", "prettier"],
  "rules": {
    "@typescript-eslint/no-unused-vars": ["warn", { "argsIgnorePattern": "^_" }]
  }
}
```

- [ ] **Step 4: Create `.prettierrc` (repo root)**

```json
{
  "tabWidth": 2,
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 88,
  "semi": true
}
```

- [ ] **Step 5: Verify lint passes on the scaffolding**

```bash
cd frontend && npm run lint && cd ../agent && npm run lint && cd ..
```
Expected: both pass (zero errors). Warnings acceptable; fix trivial unused-var warnings if present.

- [ ] **Step 6: Commit**

```bash
git add frontend/.eslintrc.json agent/.eslintrc.json .prettierrc frontend/package*.json agent/package*.json
git commit -m "chore(phase0): ESLint + Prettier config for frontend and agent"
```

---

## Task 8: Root Makefile (Feature 0.1.4 part 1)

**Files:**
- Create: `Makefile`

> **Windows note:** `make` is not standard on Windows. Each target below documents the underlying command; if `make` is unavailable, run those commands directly. On macOS/Linux `make` works natively.

- [ ] **Step 1: Create `Makefile`**

```makefile
# Arcade — common development commands.
# Windows (Git Bash): `make` may be absent; run the underlying commands manually.

.PHONY: install backend-dev frontend-dev agent-dev test lint lint-python lint-frontend lint-agent build-frontend build-agent clean

install: ## Install all dependencies (backend venv + frontend + agent)
	cd backend && pip install -r requirements.txt -r requirements-dev.txt
	cd frontend && npm install
	cd agent && npm install

backend-dev: ## Start FastAPI dev server
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend-dev: ## Start Vite dev server
	cd frontend && npm run dev

agent-dev: ## Start Electron agent
	cd agent && npm run start

test: ## Run all test suites
	cd backend && pytest
	cd frontend && npm test -- --run

lint: lint-python lint-frontend lint-agent ## Lint everything

lint-python: ## Ruff + Black + Mypy
	ruff check backend/
	black --check backend/
	mypy backend/

lint-frontend: ## ESLint frontend
	cd frontend && npm run lint

lint-agent: ## ESLint agent
	cd agent && npm run lint

build-frontend: ## Build frontend to dist/
	cd frontend && npm run build

build-agent: ## Package agent distributables
	cd agent && npm run build

clean: ## Remove build artifacts and caches
	rm -rf frontend/dist agent/dist backend/.pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
```

- [ ] **Step 2: Verify a representative target works**

```bash
make lint-python 2>/dev/null || ruff check backend/
```
Expected: ruff runs against `backend/`. (Full `make install` is verified at CHECKPOINT 0-END.)

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore(phase0): root Makefile for common dev commands"
```

---

## Task 9: CI Skeleton + PR Template (Feature 0.1.4 part 2)

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/pull_request_template.md`

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip
      - run: pip install ruff==0.8.0 black==24.10.0 mypy==1.13.0
      - run: ruff check backend/
      - run: black --check backend/
      - run: mypy backend/

  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip
      - run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - run: cd backend && pytest --maxfail=1 -q

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip
      - run: pip install bandit==1.7.11 pip-audit==2.7.3
      - run: bandit -r backend/ -x backend/tests,backend/venv
      - run: pip-audit -r backend/requirements.txt
      - name: Check for committed private keys (R-05)
        run: |
          if git ls-files | grep -iE '\.(pem|key)$'; then
            echo "Private key file detected in repo"; exit 1
          fi

  lint-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci && npm run lint

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci && npm test -- --run

  lint-agent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: agent/package-lock.json
      - run: cd agent && npm ci && npm run lint
```

- [ ] **Step 2: Create `.github/pull_request_template.md`**

```markdown
## Summary

<!-- What does this PR change and why? -->

## Testing

- [ ] `pre-commit run --all-files` passes
- [ ] `pytest backend/` passes
- [ ] `npm test` passes in frontend/ and agent/
- [ ] Manual verification steps (if applicable):

## Checklist

- [ ] No secrets / private keys committed (`*.pem`, `*.key`, `license.key`)
- [ ] Docs updated where relevant
- [ ] Linked issue / TODO task reference:
```

- [ ] **Step 3: Validate the workflow YAML locally**

```bash
python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('ci.yml OK')"
```
Expected: prints `ci.yml OK`.

- [ ] **Step 4: Commit**

```bash
git add .github/
git commit -m "ci(phase0): GitHub Actions workflow + PR template"
```

---

## Task 10: Docs Placeholders + CONTRIBUTING (Feature 0.1.4 part 3 + Phase 0 doc reqs)

**Files:**
- Create: `docs/architecture.md`, `docs/api-reference.md`, `docs/deployment.md`, `docs/agent-setup.md`, `docs/developer-guide.md`, `docs/operator-guide.md`, `docs/CONTRIBUTING.md`, `docs/security/auth-audit.md`, `docs/security/key-management.md`, `docs/security/threat-model.md`

- [ ] **Step 1: Create placeholder docs (heading + TODO note)**

For each path below, create a file whose body is a `# <Title>` heading followed by:
```markdown

> **TODO:** Document during the corresponding phase. See `docs/TODO.md` for the task that fills this in.
```

Paths:
- `docs/architecture.md` — # Architecture
- `docs/api-reference.md` — # API Reference
- `docs/deployment.md` — # Deployment Guide
- `docs/agent-setup.md` — # Agent Setup
- `docs/developer-guide.md` — # Developer Guide
- `docs/operator-guide.md` — # Operator Guide
- `docs/security/auth-audit.md` — # Authentication Audit
- `docs/security/key-management.md` — # Key Management
- `docs/security/threat-model.md` — # Threat Model

(Create `docs/security/` if it does not exist.)

- [ ] **Step 2: Create `docs/CONTRIBUTING.md`**

```markdown
# Contributing to Arcade

## Branching strategy

- `main` — protected; only via merged PR. Never push directly.
- `develop` — integration branch.
- Feature branches: `feature/<scope>-<short-desc>` (e.g. `feature/seat-service`).
- Fixes: `fix/<short-desc>`. Chores: `chore/<short-desc>`. Releases: `release/v<x.y.z>`.

## Commit message format

`type(scope): message` — types: `feat`, `fix`, `docs`, `test`, `chore`, `ci`, `refactor`, `deps`.

## Local setup

```bash
git clone https://github.com/AshminDhungana/Arcade.git
cd Arcade
# Backend (Python 3.13)
cd backend && python -m venv venv && source venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt -r requirements-dev.txt && cd ..
# Frontend + Agent (Node 24)
cd frontend && npm install && cd ../agent && npm install && cd ..
pre-commit install
```

## Before opening a PR

- `pre-commit run --all-files` passes
- `pytest backend/` passes
- `npm test` passes in `frontend/` and `agent/`
- No secrets / private keys committed
```

- [ ] **Step 3: Commit**

```bash
git add docs/
git commit -m "docs(phase0): placeholder docs + CONTRIBUTING.md"
```

---

## Task 11: CHECKPOINT 0-END Verification

Verify each CHECKPOINT 0-END criterion from `docs/TODO.md`. Run every command; record any failure.

- [ ] **Step 1: `make install` (or underlying commands) succeeds on a clean clone**

```bash
cd backend && source venv/Scripts/activate && pip install -r requirements.txt -r requirements-dev.txt && cd ..
cd frontend && npm install && cd ..
cd agent && npm install && cd ..
```
Expected: all three install without error.

- [ ] **Step 2: `pre-commit run --all-files` passes with zero errors**

```bash
pre-commit run --all-files
```
Expected: `Passed` (only cosmetic autofixes applied on first run are acceptable).

- [ ] **Step 3: `npm run lint` passes in both `frontend/` and `agent/`**

```bash
cd frontend && npm run lint && cd ../agent && npm run lint && cd ..
```
Expected: zero errors in both.

- [ ] **Step 4: `pytest backend/` runs and reports zero failures**

```bash
cd backend && pytest -q && cd ..
```
Expected: existing validation-spike tests pass (ARCH-05/06 suites); zero failures. New feature tests = zero until Phase 1.

- [ ] **Step 5: All directories from `Folder_Structure.md` are present**

```bash
for d in backend/api/routers backend/services backend/repositories backend/models backend/schemas backend/licensing backend/core backend/scripts frontend/src/pages frontend/src/components frontend/src/hooks frontend/src/api frontend/src/store frontend/src/utils agent/src/main/platform agent/src/main/storage agent/src/main/ipc agent/src/main/ws agent/src/main/health agent/src/main/tray agent/src/renderer alembic/versions tools; do
  [ -d "$d" ] && echo "OK  $d" || echo "MISSING  $d"
done
```
Expected: every line prints `OK`.

- [ ] **Step 6: Branch protection + PR template (requires repo admin)**

Using `gh` CLI (must be authenticated and a repo admin on `AshminDhungana/Arcade`):
```bash
gh api repos/AshminDhungana/Arcade/rulesets -X POST -f name="protect-main" \
  -f target=branch -f enforcement=active \
  -F 'conditions[ref_name][]=refs/heads/main' \
  -F 'rules[0][type]=deletion' \
  -F 'rules[1][type]=pull_request' \
  -f 'rules[1][parameters][required_approving_review_count]=1' \
  || echo "Branch protection needs admin — set via GitHub UI if gh fails"
```
Verify the PR template appears by opening a draft PR (or trust the file presence at `.github/pull_request_template.md`). **If you are not a repo admin, document this as deferred — do not block the rest of the checkpoint on it.**

- [ ] **Step 7: Mark Phase 0 complete in `docs/TODO.md`**

In `docs/TODO.md`, under ⚡ CHECKPOINT 0-END, check off the six items that passed. Add a one-line status note under the Project Overview noting "Phase 0 complete (validated <date> on Windows)."

- [ ] **Step 8: Final commit**

```bash
git add docs/TODO.md
git commit -m "docs(phase0): mark CHECKPOINT 0-END complete"
```

---

## Self-Review (run after writing — results recorded here)

**1. Spec coverage** — TODO.md Phase 0 features mapped:
- Feature 0.1.1 (repo/folders/gitignore/branch protection/PR template) → Tasks 1, 9 ✓
- Feature 0.1.2 (Python env + requirements) → Task 2 ✓
- Feature 0.1.2 (linters/type-checker) → Task 3 ✓
- Feature 0.1.2 (pre-commit) → Task 4 ✓
- Feature 0.1.3 (frontend scaffold) → Task 5 ✓
- Feature 0.1.3 (agent scaffold) → Task 6 ✓
- Feature 0.1.3 (TS linting) → Task 7 ✓
- Feature 0.1.4 (Makefile) → Task 8 ✓
- Feature 0.1.4 (CI skeleton) → Task 9 ✓
- Feature 0.1.4 (docs directory) → Task 10 ✓
- CHECKPOINT 0-END → Task 11 ✓
- Doc reqs (CONTRIBUTING, README Getting Started) → Task 10 ✓ (README already has content; CONTRIBUTING created)

**2. Placeholder scan** — no "TBD"/"implement later"/"add validation" without specifics; every code/config step contains the actual content. Native-module install risk is explicitly flagged with a concrete fallback, not hand-waved.

**3. Type/path consistency** — `@/` alias set identically in both frontend tsconfig and agent tsconfig; `npm run lint` script defined in both package.json files; pre-commit hook revs match the versions pinned in requirements-dev.txt (ruff 0.8.0, mypy 1.13.0, bandit 1.7.11) and CI uses the same. Agent `main` field (`dist/main/index.js`) matches the tsconfig `outDir` + stub file path.

**Known carry-over / risks (do not block Phase 0, revisit before the named phase):**
- Branch protection needs repo admin (Task 11 Step 6) — documented, deferrable.
- `better-sqlite3` native build on Node 24 (Task 6) — flagged with fallback.
- `tinytuya` / `python-escpos` import on Windows is optional for Phase 0 (Task 2 Step 4) — needed Phase 5.
- `make` on Windows (Task 8) — underlying commands documented per target.
