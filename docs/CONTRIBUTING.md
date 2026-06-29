# Contributing to Arcade

## Branching Strategy

- `main` — production-ready, protected
- `develop` — integration branch, all PRs merge here first
- `feature/<name>` — new features
- `fix/<name>` — bug fixes
- `chore/<name>` — tooling/ci/docs
- `release/<version>` — release preparation

## Commit Format

Use conventional commits: `type(scope): message`

Examples:
- `feat(phase0): scaffold backend directory structure`
- `fix(auth): correct token_version validation`
- `chore(ci): add GitHub Actions workflow`

## PR Process

1. Open PR from `feature/<name>` → `develop`
2. Fill out the PR template completely
3. Ensure CI passes (all 5 jobs green)
4. Get at least 1 review approval
5. Squash-merge with descriptive commit message

## Local Setup

```bash
make install    # Install all deps
make lint       # Run all linters
make test       # Run all tests
make backend-dev  # Start FastAPI dev server
make frontend-dev # Start Vite dev server
```
