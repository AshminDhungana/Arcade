# Design: Fix failing check-secrets CI job (gitleaks action)

Date: 2026-08-13
Status: Approved

## Problem

The `check-secrets` job in `.github/workflows/security.yml` fails on every run. The log shows:

```
Warning: Unexpected input(s) 'config', 'args', valid inputs are ['']
Error: 🛑 missing gitleaks license. Go grab one at gitleaks.io and store it as a GitHub Secret named GITLEAKS_LICENSE.
```

Two breaking changes in `gitleaks/gitleaks-action@v3` cause this:

1. v3 removed the `config` and `args` inputs; passing them is invalid and they are silently ignored.
2. v3 now requires a paid license key stored as the `GITLEAKS_LICENSE` GitHub secret; without it the action exits with an error.

The project's `.gitleaks.toml` config is unaffected and remains valid.

## Chosen approach

Pin the action to its last license-free, input-compatible major version:

```
gitleaks/gitleaks-action@v3  ->  gitleaks/gitleaks-action@v2
```

`@v2` (a moving tag) resolves to the latest v2 release — currently v2.3.9 (verified via `git ls-remote` on 2026-08-13). It:

- accepts the `config` and `args` inputs (eliminates the invalid-input warning),
- requires no license key (eliminates the `missing gitleaks license` error),
- is a Docker-based action that runs `gitleaks detect` against the repository,
- writes the JSON report to `gitleaks-report.json` via the existing `args`, which the subsequent `actions/upload-artifact@v4` step already uploads.

## Alternatives considered

| Option | Trade-off |
| --- | --- |
| Run gitleaks CLI directly (download release binary) | No license, full control; but no longer uses the official action and needs a binary download step. |
| Add `GITLEAKS_LICENSE` secret, keep v3 | Official path, but requires registering at gitleaks.io and manual secret setup; v3 also ignores the existing `config`/`args` inputs, requiring workflow rewrites. |

## Changes

Single edit in `.github/workflows/security.yml`:

- Line 66: `uses: gitleaks/gitleaks-action@v3` → `uses: gitleaks/gitleaks-action@v2`

Everything else in the job stays as-is:

- `actions/checkout@v6` with `fetch-depth: 0` (full history for gitleaks)
- `config: .gitleaks.toml` (project config; allowed to stay in repo per allowlist)
- `args: "--verbose --redact --report-format json --report-path gitleaks-report.json"`
- `actions/upload-artifact@v4` upload of `gitleaks-report.json`

## Out of scope

- Upgrading to v3 with a license
- Any change to `.gitleaks.toml` allowlist rules
- Other jobs in `security.yml` (bandit, pip-audit, npm audit, sensitive-file checks) — they are not failing

## Verification

The change is a CI-only workflow edit. Verification is:

1. Workflow YAML still parses (no syntax error) after the edit.
2. Push to `develop` triggers the `Security` workflow; the `check-secrets` job must pass (no invalid-input warning, no license error).
3. `gitleaks-report.json` artifact is produced and uploaded.

## Acceptance criteria

- [ ] `check-secrets` job completes successfully without a `GITLEAKS_LICENSE` secret
- [ ] No `Unexpected input(s)` warning for `config`/`args`
- [ ] `gitleaks-report.json` artifact uploaded
