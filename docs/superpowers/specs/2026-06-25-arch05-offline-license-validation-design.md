# ARCH-05 — Offline Ed25519 License Flow Validation (Design)

**Date:** 2026-06-25
**Author:** Ashmin Dhungana
**Status:** Design — approved (Approach A)
**Scope:** Windows only. macOS and Linux are deferred and explicitly flagged in both this spec and `docs/TODO.md`.
**References:** `docs/TODO.md` (ARCH-05), `docs/Arcade_SRS.md` §FR-LIC-001…014, FR-SYS-008, `docs/Arcade_SDD.md` §16, `docs/references/ARCH-01/02/03-*.md` (precedent).

---

## 1. Purpose

ARCH-05 in `docs/TODO.md` requires validating the offline licensing architecture before any Phase 1 feature development begins:

> **ARCH-05: Validate Ed25519 offline license flow end-to-end**
> - Generate a keypair; sign a test license payload; verify on a different machine
> - Confirm `py-machineid` produces a stable hardware ID on Windows and Linux (reboot-stable, not session-specific)
> - Confirm `py-machineid` requires no admin privileges on all three OSes
> - **Pass criteria:** Hardware ID is identical across reboots; license verification passes; hardware mismatch is correctly detected

This task follows the precedent set by ARCH-01, ARCH-02, and ARCH-03: a **self-contained validation spike** in `backend/tests/validation_tasks/arch05/` plus a written `docs/references/ARCH-05-*.md` report. It is **not** the Phase 1 implementation of `backend/licensing/*` or `tools/keygen/` (Features 1.2.1–1.2.5). Those modules will lift this spike's cryptography verbatim once the approach is proven.

### Scope decision (user-approved)

The pass criterion "verify on a different machine" cannot be satisfied with real second hardware in this environment (single Windows machine available). Per the user's direction:

- Validate **Windows only**.
- The "different machine → reject" criterion is proven by **injecting a foreign hardware ID** (license signed against hwid-A, verified against hwid-B) and asserting `HARDWARE_MISMATCH`.
- Record "validated for Windows only; macOS/Linux deferred" in both the report (`docs/references/ARCH-05-*.md`) and the `docs/TODO.md` entry.

---

## 2. Requirements traced

| Requirement | Source | How the spike satisfies it |
|---|---|---|
| Ed25519 signing, public key only embedded | FR-LIC-001, SDD §16.2 | PyNaCl keypair generated at runtime; verify uses only the public half |
| `py-machineid` primary, SHA-256 fallback, no admin | FR-LIC-002, SDD §16.3 | `get_hardware_id()` uses `machineid.id()`; suite runs unelevated |
| Copyable Hardware ID | FR-LIC-003 | `get_hardware_id()` returns a stable 32-hex string |
| Offline keygen tool | FR-LIC-004, SDD §16.5 | `generate_license()` in the spike |
| Signed (not encrypted) JSON payload, base64 envelope | FR-LIC-005, SDD §16.4 | Envelope = `base64(json({payload, signature}))`; signature over canonical JSON |
| Verify signature + hardware match | FR-LIC-007, SDD §16.6 | `check_license()` full flow |
| Distinguish invalid signature vs hardware mismatch vs trial expired vs missing | FR-LIC-008, SDD §16.6/16.7 | `LicenseError` enum, one parametrized case each |
| Re-verify on every launch (offline) | FR-SYS-008, FR-LIC-009 | `check_license()` is a pure local function — no network code present |
| Trial expiry | FR-LIC-011, SDD §16.9 | `TRIAL_EXPIRED` case + `TRIAL valid` case |
| Hardware-change re-activation | FR-LIC-010, SDD §16.8 | Proven by the foreign-hwid rejection case |

Out of scope for this validation (Phase 1): Tkinter Activation UI (FR-LIC-003/006/008 display, Feature 1.2.5), `license_status` DB cache (FR-LIC-012/014), tamper-doesn't-crash behavior beyond `check_license()`'s return (FR-LIC-013's broader Launcher-level guarantee).

---

## 3. Spike design

### 3.1 File layout

```
backend/tests/validation_tasks/arch05/
├── __init__.py
├── arch05_lib.py     ← minimal reimplementation of SDD §16.3–16.6 (NOT backend/licensing/*)
├── conftest.py       ← fixtures: ephemeral keypair, tmp license.key, hwid injection
└── test_arch05.py    ← parametrized pytest over all outcomes + tamper cases
```

### 3.2 `arch05_lib.py` — mirrors SDD §16.3–16.6 exactly

Public API (function names and semantics chosen to be liftable verbatim into Phase 1):

- `get_hardware_id() -> str`
  - Primary: `machineid.id()`. If non-empty, `raw = f"py-machineid:{machine_id}"`.
  - Fallback: SHA-256 over joined OS identifiers (per SDD §16.3; full fallback command detail is Phase 1 — the spike only needs the `py-machineid` path on Windows, which is the validated OS).
  - Returns `hashlib.sha256(raw.encode()).hexdigest()[:32]`.
  - **Injectable**: reads `ARCADE_TEST_HWID` from the environment; if set, returned verbatim (bypasses the machine call). This is how the "different machine" case is made deterministic without second hardware.

- `class LicenseError(Enum)` — `MISSING`, `INVALID_SIGNATURE`, `HARDWARE_MISMATCH`, `TRIAL_EXPIRED` (SDD §16.6).

- `@dataclass class LicenseResult` — `ok: bool`, `error: LicenseError | None`, `payload: dict | None`.

- `generate_keypair() -> tuple[str, str]` — returns `(private_key_hex, public_key_hex)` via `nacl.signing.SigningKey.generate()`.

- `generate_license(private_key_hex, hardware_id, cafe_name, license_type="PERPETUAL", trial_days=None, issue_date=None) -> str`
  - Builds `payload` dict per SDD §16.4 (`cafe_name`, `hardware_id`, `license_type`, `issue_date`, `trial_expires_at`).
  - `canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()`.
  - `signature = SigningKey(bytes.fromhex(private_key_hex)).sign(canonical).signature`.
  - Returns `base64.b64encode(json.dumps({"payload": payload, "signature": base64.b64encode(signature).decode()}).encode()).decode()`.

- `check_license(license_path, public_key_hex, hardware_id=None) -> LicenseResult`
  - `hardware_id` defaults to `get_hardware_id()`; passing it explicitly is how the foreign-hwid case is driven.
  - Flow per SDD §16.6: missing → `MISSING`; base64-decode + JSON-parse; recompute canonical; `VerifyKey.verify` (catch `BadSignatureError` → `INVALID_SIGNATURE`); compare hwid → `HARDWARE_MISMATCH`; trial expiry check → `TRIAL_EXPIRED`; else `ok=True`.

### 3.3 `test_arch05.py` — parametrized cases

| # | Case | Expected result |
|---|---|---|
| 1 | Round-trip: valid keypair, valid license, matching hwid | `ok=True`, payload matches |
| 2 | No `license.key` file | `MISSING` |
| 3 | Payload byte tampered after signing | `INVALID_SIGNATURE` |
| 4 | Signed with key A, verified with key B | `INVALID_SIGNATURE` |
| 5 | Corrupted signature (random bytes) | `INVALID_SIGNATURE` |
| 6 | License bound to hwid-A, verified with hwid-B (foreign machine proxy) | `HARDWARE_MISMATCH` |
| 7 | `TRIAL` with `trial_expires_at` = yesterday | `TRIAL_EXPIRED` |
| 8 | `TRIAL` with `trial_expires_at` = tomorrow | `ok=True` |
| 9 | `get_hardware_id()` idempotent within process (Windows reboot-stability proxy) | two calls identical |
| 10 | `py-machineid` returns non-empty with no elevation | non-empty string, suite itself proves no-admin |

Cases 1–8 are parametrized over `LicenseResult` outcomes. Case 6 is the "different machine" criterion. Case 9 asserts idempotency, not true reboot-stability (see §5 caveat). Case 10 is implicit (the suite runs unelevated and `machineid.id()` returns a value) plus an explicit non-empty assertion.

### 3.4 `conftest.py` fixtures

- `keypair` (session): `generate_keypair()` → `(priv_hex, pub_hex)`.
- `tmp_license_factory` (function): returns a callable `(hwid, **license_kwargs) -> Path` that writes a `license.key` to a `tmp_path` and returns its path.
- `clean_hwid_env` (function): `monkeypatch.delenv("ARCADE_TEST_HWID", raising=False)` so the real machine ID is used by default unless a test sets it.

---

## 4. Repository changes

1. **`backend/requirements.txt`** — add `PyNaCl==1.5.0` and `py-machineid==0.6.0` (currently absent; versions per SDD §16 / TODO pinned set). Install into the venv.
2. **`.gitignore`** — add `*.pem`, `*.key`, `private_key*`, `license.key`, `tools/keygen/private_key.pem`. **This R-05 mitigation is currently missing** and is a hard precondition for any licensing work; fixing it here is in scope.
3. **`docs/references/ARCH-05-offline-license-validation.md`** — the report (~180 lines, ARCH-02/03 length): summary table, what was validated, "Windows only" caveat, keygen custody notes, manual reboot-checklist item, carry-over-to-Phase-1 table.
4. **`docs/TODO.md`** — check `[x]` on ARCH-05 and annotate "**Validated Windows only — macOS/Linux deferred**" per the user's explicit instruction.

### Out of scope (Phase 1)

`backend/licensing/{fingerprint,verify,public_key}.py`, `tools/keygen/generate_license.py`, the Tkinter launcher (Feature 1.2.5), the `license_status` table (FR-LIC-014). The spike proves the cryptography; Phase 1 ships the production modules.

---

## 5. Caveats and explicit scope cuts

- **Windows only.** macOS and Linux `py-machineid` + no-admin behavior are not validated and are flagged in the report and TODO.
- **Reboot-stability is a manual checklist item.** The spike proves `get_hardware_id()` is idempotent *within a process*; it cannot prove invariance across a real reboot without a reboot. The report will list "reboot this machine, re-run `pytest`, confirm identical hwid" as a one-step manual verification to perform before Phase 1.
- **"Different machine" is proxied**, not literal: by injecting a foreign hardware ID (case 6). The cryptographic and comparison logic that would reject a real second machine is identical to what rejects the injected foreign ID, so the proof is sound; only the physical hardware is substituted.

---

## 6. Success criteria for the validation

The ARCH-05 spike is complete when:

1. `pytest backend/tests/validation_tasks/arch05/` passes all 10 cases on Windows, unelevated, with no network.
2. `docs/references/ARCH-05-offline-license-validation.md` is written and matches the ARCH-02/03 reference format.
3. `docs/TODO.md` ARCH-05 is checked `[x]` with the Windows-only annotation.
4. `.gitignore` contains the R-05 private-key patterns.
5. The report's "carry-over to Phase 1" table identifies exactly which functions should be lifted verbatim into `backend/licensing/*`.
