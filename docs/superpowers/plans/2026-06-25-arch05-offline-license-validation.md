# ARCH-05 Offline License Flow Validation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the Ed25519 offline license architecture (keygen → sign → verify → hardware binding → trial expiry) on Windows via a self-contained pytest spike, then write the `docs/references/ARCH-05-*.md` report.

**Architecture:** A throwaway spike under `backend/tests/validation_tasks/arch05/` that reimplements SDD §16.3–16.6 in miniature (`arch05_lib.py`), driven by a parametrized pytest suite (`test_arch05.py`) over all 5 `check_license()` outcomes plus 3 tamper cases. The "different machine → reject" criterion is proven by injecting a foreign hardware ID (no second physical machine available — Windows-only, per user direction). The spike proves the cryptography; Phase 1 lifts these functions into `backend/licensing/*`.

**Tech Stack:** Python 3.13 (in `backend/venv/`), pytest, PyNaCl 1.5.0 (Ed25519), py-machineid 0.6.0 (hardware fingerprint). All synchronous — no pytest-asyncio needed.

**Spec:** `docs/superpowers/specs/2026-06-25-arch05-offline-license-validation-design.md`

**Environment notes (verified before writing this plan):**
- The venv is at `backend/venv/` and invoked as `./backend/venv/Scripts/python.exe` (Windows).
- pytest, PyNaCl, and py-machineid are **not yet installed** — Task 1 installs all three.
- No `pytest.ini`/`pyproject.toml`/`conftest.py` exists in the repo; default pytest discovery is used.
- `.gitignore` currently has **no** entries for `*.pem`/`*.key`/`private_key*`/`license.key`/`keygen` — Task 2 adds them (R-05 mitigation, a precondition for safe licensing work).
- Precedent check: ARCH-01 used a runnable async script (no pytest); ARCH-03 used a self-test script. This spike uses pytest deliberately — 10 discrete outcomes are a natural fit for parametrization, and it leaves a reusable regression suite for Phase 1.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `backend/requirements.txt` | Modify | Add `PyNaCl==1.5.0`, `py-machineid==0.6.0`, `pytest==8.2.0` |
| `.gitignore` | Modify | Add R-05 private-key / license-file ignore patterns |
| `backend/tests/validation_tasks/arch05/__init__.py` | Create | Make `arch05` an importable package |
| `backend/tests/validation_tasks/arch05/arch05_lib.py` | Create | Minimal reimplementation of SDD §16.3–16.6: fingerprint, keygen, verify |
| `backend/tests/validation_tasks/arch05/conftest.py` | Create | pytest fixtures: keypair, tmp license factory, hwid env cleanup |
| `backend/tests/validation_tasks/arch05/test_arch05.py` | Create | Parametrized suite: 8 outcome/tamper cases + idempotency + no-admin check |
| `docs/references/ARCH-05-offline-license-validation.md` | Create | The validation report (ARCH-02/03 format) |
| `docs/TODO.md` | Modify | Check `[x]` ARCH-05 + "Windows only" annotation |

**Import convention:** tests import the spike library as a sibling package. Because `arch05/` is a package (has `__init__.py`) sitting under `backend/tests/validation_tasks/`, and pytest adds the rootdir of each test file's package to `sys.path` (rootdir-based import mode), `from arch05.arch05_lib import ...` resolves. The `conftest.py` co-located in the package keeps fixtures scoped to these tests only.

---

## Task 1: Install dependencies and pin them in requirements.txt

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add the three dependencies to requirements.txt**

Append these lines to `backend/requirements.txt` (current contents are the 5 lines `fastapi`/`sqlalchemy`/`aiosqlite`/`uvicorn`/`httpx`; append after them):

```
PyNaCl==1.5.0
py-machineid==0.6.0
pytest==8.2.0
```

- [ ] **Step 2: Install them into the venv**

Run:
```bash
./backend/venv/Scripts/python.exe -m pip install PyNaCl==1.5.0 py-machineid==0.6.0 pytest==8.2.0
```
Expected: all three install with `Successfully installed ...` (PyInstaller / cryptography / cffi may already be satisfied transitively). Note the exact installed versions printed — the report (Task 8) records them.

- [ ] **Step 3: Verify all three import**

Run:
```bash
./backend/venv/Scripts/python.exe -c "import nacl.signing, machineid, pytest; print('nacl ok'); print('machineid ok'); print('pytest', pytest.__version__)"
```
Expected output:
```
nacl ok
machineid ok
pytest 8.2.0
```

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "deps: add PyNaCl, py-machineid, pytest for ARCH-05 validation"
```

---

## Task 2: Add R-05 private-key / license-file ignore patterns

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Append the Arcade-specific security block**

Append to the end of `.gitignore` (after the `*.rej` line at the file's current end):

```
# ===============================
# Arcade — Licensing / Secrets (R-05)
# ===============================
# Ed25519 keygen private key — NEVER committed (lives out-of-band on seller machine)
tools/keygen/private_key.pem
private_key.pem
*.pem
# License files (issued per-customer, placed at runtime, never in VCS)
license.key
*.license
# Generic private key material
*.key
private_key*
```

- [ ] **Step 2: Verify the patterns ignore a planted private key**

Run:
```bash
echo "fake-private-key-bytes" > private_key.pem && echo "fake" > license.key && git check-ignore private_key.pem license.key && rm private_key.pem license.key
```
Expected: `git check-ignore` prints both paths (meaning they ARE ignored) and exits 0. The `rm` cleans up the throwaway files. If `check-ignore` prints nothing / exits non-zero, the patterns are wrong — fix before continuing.

- [ ] **Step 3: Confirm no real secrets are currently tracked**

Run:
```bash
git ls-files | grep -iE "\.(pem|key)$|license\.key|private_key" || echo "CLEAN: no tracked secrets"
```
Expected: `CLEAN: no tracked secrets`. (There are none today; this is a guard against future mistakes and confirms the baseline.)

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore Ed25519 private key + license.key (R-05 mitigation)"
```

---

## Task 3: Create the arch05 package skeleton + verify pytest discovery

**Files:**
- Create: `backend/tests/validation_tasks/arch05/__init__.py`
- Create: `backend/tests/validation_tasks/arch05/test_arch05.py` (placeholder)
- Create: `backend/tests/validation_tasks/arch05/conftest.py` (placeholder)

- [ ] **Step 1: Create the package marker**

Create `backend/tests/validation_tasks/arch05/__init__.py` with exactly:

```python
"""ARCH-05 validation spike: Ed25519 offline license flow.

Self-contained reimplementation of the licensing cryptography described in
SDD §16 (fingerprint / keygen / verify). This is a validation spike, NOT the
Phase 1 production module backend/licensing/* — it lives under tests/ on
purpose. Phase 1 lifts these functions verbatim once the approach is proven.
"""
```

- [ ] **Step 2: Create a placeholder test that establishes discovery works**

Create `backend/tests/validation_tasks/arch05/test_arch05.py` with exactly:

```python
"""ARCH-05 validation tests.

Each case drives check_license() to a specific LicenseResult outcome or
tamper-rejection, mirroring SDD §16.6 and FR-LIC-007/008. Cases are built out
in Tasks 5-7; this placeholder only proves pytest discovery works.
"""


def test_discovery_smoke():
    """Proves pytest discovers this package before any real code exists."""
    assert True
```

- [ ] **Step 3: Create a placeholder conftest**

Create `backend/tests/validation_tasks/arch05/conftest.py` with exactly:

```python
"""Shared fixtures for the ARCH-05 validation spike.

Populated in Task 5; this placeholder exists so the package's fixture module
is in place during the discovery check.
"""
```

- [ ] **Step 4: Run pytest and confirm discovery**

Run:
```bash
./backend/venv/Scripts/python.exe -m pytest backend/tests/validation_tasks/arch05/ -v
```
Expected: `1 passed`, with the test name `test_discovery_smoke` listed. If pytest fails with a collection/import error, the package layout is wrong — confirm `__init__.py` exists and the path matches.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/validation_tasks/arch05/
git commit -m "test(arch05): package skeleton + pytest discovery check"
```

---

## Task 4: Implement arch05_lib.py (fingerprint, keygen, verify)

**Files:**
- Create: `backend/tests/validation_tasks/arch05/arch05_lib.py`

This task is written test-first within itself (the functions are pure and the spec mandates exact behavior), but because `arch05_lib.py` is a *library* consumed by the test suite rather than a feature, the tests live in Task 5+. Here we implement the library; Task 5 then pins its behavior with tests. This ordering matches "library, then its tests" for a spike.

- [ ] **Step 1: Write arch05_lib.py with all five components**

Create `backend/tests/validation_tasks/arch05/arch05_lib.py` with exactly:

```python
"""ARCH-05 spike library — minimal reimplementation of SDD §16.3-16.6.

NOT backend/licensing/*. Lifted verbatim into Phase 1 once validated.
All functions are synchronous (the licensing flow has no I/O that benefits
from async).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional

import machineid  # py-machineid
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError


# ---------------------------------------------------------------------------
# 16.3 Hardware fingerprinting
# ---------------------------------------------------------------------------

def get_hardware_id() -> str:
    """Return a stable 32-hex Hardware ID.

    Primary source: py-machineid (no admin, cross-platform). SHA-256 fallback
    chain (SDD §16.3) is only used if py-machineid returns empty; on the
    validated OS (Windows) the primary path is taken.

    Test injection: if env var ARCADE_TEST_HWID is set, it is returned verbatim
    so tests can simulate a "different machine" deterministically.
    """
    override = os.environ.get("ARCADE_TEST_HWID")
    if override:
        return override

    machine_id = machineid.id()  # py-machineid's public API is .id()
    if machine_id:
        raw = f"py-machineid:{machine_id}"
    else:
        # Fallback: hash whatever identifiers we can gather. The spike only
        # needs a deterministic non-empty value here; full per-OS command set is
        # Phase 1 (validated OS is Windows, where the primary path is taken).
        import platform
        import uuid
        fallback_parts = [platform.node(), str(uuid.getnode())]
        raw = "|".join(p for p in fallback_parts if p)

    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# 16.6 Result types
# ---------------------------------------------------------------------------

class LicenseError(Enum):
    MISSING = "no license.key found"
    INVALID_SIGNATURE = "signature verification failed"
    HARDWARE_MISMATCH = "license is bound to a different machine"
    TRIAL_EXPIRED = "trial period has ended"


@dataclass
class LicenseResult:
    ok: bool
    error: Optional[LicenseError] = None
    payload: Optional[dict] = None


# ---------------------------------------------------------------------------
# 16.5 Keygen (internal only)
# ---------------------------------------------------------------------------

def generate_keypair() -> tuple[str, str]:
    """Generate a fresh Ed25519 keypair. Returns (private_key_hex, public_key_hex)."""
    signing_key = SigningKey.generate()
    private_hex = signing_key.encode().hex()
    public_hex = signing_key.verify_key.encode().hex()
    return private_hex, public_hex


def generate_license(
    private_key_hex: str,
    hardware_id: str,
    cafe_name: str,
    license_type: str = "PERPETUAL",
    trial_days: Optional[int] = None,
    issue_date: Optional[str] = None,
) -> str:
    """Sign and envelope a license payload. Returns base64-encoded license string.

    Payload + signature scheme per SDD §16.4/16.5: signature is over canonical
    (sorted-key, no-whitespace) JSON of the payload; the whole thing is wrapped
    as base64(json({payload, signature})) for transport.
    """
    if issue_date is None:
        issue_date = date.today().isoformat()
    trial_expires_at = None
    if license_type == "TRIAL" and trial_days is not None:
        trial_expires_at = (date.today() + timedelta(days=trial_days)).isoformat()

    payload = {
        "cafe_name": cafe_name,
        "hardware_id": hardware_id,
        "license_type": license_type,
        "issue_date": issue_date,
        "trial_expires_at": trial_expires_at,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signing_key = SigningKey(bytes.fromhex(private_key_hex))
    signature = signing_key.sign(canonical).signature

    envelope = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode(),
    }
    return base64.b64encode(json.dumps(envelope).encode()).decode()


# ---------------------------------------------------------------------------
# 16.6 Verification flow
# ---------------------------------------------------------------------------

def check_license(
    license_path: str,
    public_key_hex: str,
    hardware_id: Optional[str] = None,
) -> LicenseResult:
    """Verify a license.key file. Returns a LicenseResult (never raises on
    license failures; only on corrupt/unparseable files).

    hardware_id defaults to get_hardware_id(); passing it explicitly is how the
    foreign-machine rejection case is driven in tests.
    """
    if not os.path.exists(license_path):
        return LicenseResult(ok=False, error=LicenseError.MISSING)

    try:
        raw = base64.b64decode(open(license_path, "rb").read())
        parsed = json.loads(raw)
        payload = parsed["payload"]
        signature = base64.b64decode(parsed["signature"])
    except (ValueError, KeyError, json.JSONDecodeError):
        # Malformed envelope = not a valid license file.
        return LicenseResult(ok=False, error=LicenseError.INVALID_SIGNATURE)

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    try:
        VerifyKey(bytes.fromhex(public_key_hex)).verify(canonical, signature)
    except BadSignatureError:
        return LicenseResult(ok=False, error=LicenseError.INVALID_SIGNATURE)

    if hardware_id is None:
        hardware_id = get_hardware_id()
    if payload["hardware_id"] != hardware_id:
        return LicenseResult(ok=False, error=LicenseError.HARDWARE_MISMATCH)

    if payload["license_type"] == "TRIAL":
        trial_expires_at = payload.get("trial_expires_at")
        if trial_expires_at and date.today() > date.fromisoformat(trial_expires_at):
            return LicenseResult(ok=False, error=LicenseError.TRIAL_EXPIRED)

    return LicenseResult(ok=True, payload=payload)
```

- [ ] **Step 2: Verify the library imports cleanly**

Run:
```bash
./backend/venv/Scripts/python.exe -c "from arch05.arch05_lib import get_hardware_id, generate_keypair, generate_license, check_license, LicenseError, LicenseResult; print('import ok')"
```
Expected: `import ok`. If you get `ModuleNotFoundError: arch05`, run from the directory containing the package or set `PYTHONPATH=backend/tests/validation_tasks`. (The pytest run in later tasks sets this implicitly via rootdir discovery.)

- [ ] **Step 3: Smoke-test the full happy path by hand**

Run:
```bash
./backend/venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'backend/tests/validation_tasks')
from arch05.arch05_lib import *
priv, pub = generate_keypair()
hwid = get_hardware_id()
print('hwid:', hwid, 'len', len(hwid))
lic = generate_license(priv, hwid, 'Test Cafe')
open('/tmp/arch05_lic.key','wb').write(lic.encode())
r = check_license('/tmp/arch05_lic.key', pub)
print('result:', r.ok, r.error)
import os; os.remove('/tmp/arch05_lic.key')
"
```
Expected: `hwid:` a 32-hex string with `len 32`, then `result: True None`. This proves end-to-end before the tests pin it.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/validation_tasks/arch05/arch05_lib.py
git commit -m "feat(arch05): spike library — fingerprint, keygen, verify (SDD §16.3-16.6)"
```

---

## Task 5: Implement conftest.py fixtures

**Files:**
- Modify: `backend/tests/validation_tasks/arch05/conftest.py`

- [ ] **Step 1: Replace the placeholder conftest with real fixtures**

Overwrite `backend/tests/validation_tasks/arch05/conftest.py` with exactly:

```python
"""Shared fixtures for the ARCH-05 validation spike."""
from __future__ import annotations

import pytest

from arch05.arch05_lib import generate_keypair, generate_license


@pytest.fixture(scope="session")
def keypair() -> tuple[str, str]:
    """A single Ed25519 keypair shared across the whole session."""
    return generate_keypair()


@pytest.fixture
def foreign_keypair() -> tuple[str, str]:
    """A second, independent keypair for the 'wrong key' tamper case."""
    return generate_keypair()


@pytest.fixture
def tmp_license_factory(tmp_path):
    """Return a callable that writes a license.key to a clean tmp dir.

    Usage: path = tmp_license_factory(hwid, cafe_name="X", ...)
    Each call writes to the same file (license.key) inside a fresh tmp_path.
    """
    def _make(
        private_key_hex: str,
        hardware_id: str,
        cafe_name: str = "Test Cafe",
        license_type: str = "PERPETUAL",
        trial_days: int | None = None,
    ):
        license_path = tmp_path / "license.key"
        blob = generate_license(
            private_key_hex,
            hardware_id,
            cafe_name,
            license_type=license_type,
            trial_days=trial_days,
        )
        license_path.write_text(blob)
        return str(license_path)

    return _make
```

- [ ] **Step 2: Verify fixtures load (run the smoke test, which needs no fixture)**

Run:
```bash
./backend/venv/Scripts/python.exe -m pytest backend/tests/validation_tasks/arch05/ -v
```
Expected: still `1 passed` (the smoke test from Task 3), but now with no import errors from conftest. If conftest fails to import, the `from arch05.arch05_lib import ...` line can't resolve — confirm `__init__.py` exists in both `arch05/` and that pytest is invoked so rootdir discovery finds the package.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/validation_tasks/arch05/conftest.py
git commit -m "test(arch05): pytest fixtures — keypair, foreign keypair, tmp license factory"
```

---

## Task 6: Write the round-trip and MISSING + tamper tests (cases 1–5)

**Files:**
- Modify: `backend/tests/validation_tasks/arch05/test_arch05.py`

- [ ] **Step 1: Replace the placeholder test file with cases 1–5**

Overwrite `backend/tests/validation_tasks/arch05/test_arch05.py` with exactly:

```python
"""ARCH-05 validation tests — SDD §16.6 outcomes + tamper cases.

Cases 1-5: round-trip, MISSING, and the three INVALID_SIGNATURE variants.
Cases 6-10 are added in Task 7.
"""
from __future__ import annotations

import base64
import json

from arch05.arch05_lib import LicenseError, check_license, generate_license, get_hardware_id


# ---------------------------------------------------------------------------
# Case 1: round-trip happy path
# ---------------------------------------------------------------------------

def test_round_trip_valid_license(keypair, tmp_license_factory):
    priv, pub = keypair
    hwid = get_hardware_id()
    path = tmp_license_factory(priv, hwid, cafe_name="Galaxy Gaming Lounge")

    result = check_license(path, pub)

    assert result.ok is True
    assert result.error is None
    assert result.payload["cafe_name"] == "Galaxy Gaming Lounge"
    assert result.payload["hardware_id"] == hwid
    assert result.payload["license_type"] == "PERPETUAL"


# ---------------------------------------------------------------------------
# Case 2: no license.key file
# ---------------------------------------------------------------------------

def test_missing_license_file(keypair, tmp_path):
    _, pub = keypair
    missing_path = str(tmp_path / "does_not_exist.key")

    result = check_license(missing_path, pub)

    assert result.ok is False
    assert result.error is LicenseError.MISSING


# ---------------------------------------------------------------------------
# Case 3: payload byte tampered after signing
# ---------------------------------------------------------------------------

def test_invalid_signature_payload_tampered(keypair, tmp_path):
    priv, pub = keypair
    hwid = get_hardware_id()

    # Build a valid license, then mutate one byte of the cafe_name in the
    # already-signed payload. The signature no longer matches.
    blob = generate_license(priv, hwid, cafe_name="Galaxy Gaming Lounge")
    envelope = json.loads(base64.b64decode(blob))
    envelope["payload"]["cafe_name"] = "Malaxy Gaming Lounge"  # G -> M
    tampered_blob = base64.b64encode(json.dumps(envelope).encode()).decode()

    path = tmp_path / "license.key"
    path.write_text(tampered_blob)

    result = check_license(str(path), pub)

    assert result.ok is False
    assert result.error is LicenseError.INVALID_SIGNATURE


# ---------------------------------------------------------------------------
# Case 4: signed with key A, verified with key B
# ---------------------------------------------------------------------------

def test_invalid_signature_wrong_key(keypair, foreign_keypair, tmp_license_factory):
    priv_a, _ = keypair          # signs the license
    _, pub_b = foreign_keypair   # tries to verify
    hwid = get_hardware_id()
    path = tmp_license_factory(priv_a, hwid)

    result = check_license(path, pub_b)

    assert result.ok is False
    assert result.error is LicenseError.INVALID_SIGNATURE


# ---------------------------------------------------------------------------
# Case 5: corrupted signature (random bytes)
# ---------------------------------------------------------------------------

def test_invalid_signature_corrupted(keypair, tmp_path):
    priv, pub = keypair
    hwid = get_hardware_id()

    blob = generate_license(priv, hwid, cafe_name="Test Cafe")
    envelope = json.loads(base64.b64decode(blob))
    # Replace the signature with 64 random-ish bytes (Ed25519 sig is 64 bytes).
    envelope["signature"] = base64.b64encode(b"\x00" * 64).decode()
    corrupted_blob = base64.b64encode(json.dumps(envelope).encode()).decode()

    path = tmp_path / "license.key"
    path.write_text(corrupted_blob)

    result = check_license(str(path), pub)

    assert result.ok is False
    assert result.error is LicenseError.INVALID_SIGNATURE
```

- [ ] **Step 2: Run the suite and confirm all 5 pass**

Run:
```bash
./backend/venv/Scripts/python.exe -m pytest backend/tests/validation_tasks/arch05/ -v
```
Expected: `5 passed`, listing:
- `test_round_trip_valid_license PASSED`
- `test_missing_license_file PASSED`
- `test_invalid_signature_payload_tampered PASSED`
- `test_invalid_signature_wrong_key PASSED`
- `test_invalid_signature_corrupted PASSED`

If any tamper case returns a *different* error than `INVALID_SIGNATURE` (e.g. `HARDWARE_MISMATCH`), the `check_license` ordering is wrong — re-check that signature verification happens before the hardware compare (SDD §16.6 ordering).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/validation_tasks/arch05/test_arch05.py
git commit -m "test(arch05): cases 1-5 — round-trip, MISSING, 3 INVALID_SIGNATURE variants"
```

---

## Task 7: Write hardware-mismatch, trial, and hardware-id checks (cases 6–10)

**Files:**
- Modify: `backend/tests/validation_tasks/arch05/test_arch05.py`

- [ ] **Step 1: Append cases 6–10 to the test file**

Append the following to the end of `backend/tests/validation_tasks/arch05/test_arch05.py` (after case 5):

```python


# ---------------------------------------------------------------------------
# Case 6: license bound to hwid-A, verified against hwid-B (foreign machine)
# This is the "verify on a different machine -> reject" criterion. Proven by
# injecting a foreign hardware ID rather than a second physical machine
# (single Windows machine available; macOS/Linux deferred).
# ---------------------------------------------------------------------------

def test_hardware_mismatch_rejects_foreign_machine(keypair, tmp_license_factory):
    priv, pub = keypair
    # License is bound to this real machine's hardware ID...
    real_hwid = get_hardware_id()
    path = tmp_license_factory(priv, real_hwid, cafe_name="Bound Machine")

    # ...but we verify as if we are a DIFFERENT machine by passing a foreign ID.
    foreign_hwid = "f" * 32  # 32-hex, guaranteed != real_hwid
    assert foreign_hwid != real_hwid

    result = check_license(path, pub, hardware_id=foreign_hwid)

    assert result.ok is False
    assert result.error is LicenseError.HARDWARE_MISMATCH


# ---------------------------------------------------------------------------
# Case 7: TRIAL expired (trial_expires_at = yesterday)
# ---------------------------------------------------------------------------

def test_trial_expired(keypair, tmp_license_factory):
    priv, pub = keypair
    hwid = get_hardware_id()
    # trial_days=-1 -> trial_expires_at = yesterday (timedelta handles negatives).
    path = tmp_license_factory(
        priv, hwid, cafe_name="Expired Trial", license_type="TRIAL", trial_days=-1
    )

    result = check_license(path, pub)

    assert result.ok is False
    assert result.error is LicenseError.TRIAL_EXPIRED


# ---------------------------------------------------------------------------
# Case 8: TRIAL still valid (trial_expires_at = tomorrow)
# ---------------------------------------------------------------------------

def test_trial_still_valid(keypair, tmp_license_factory):
    priv, pub = keypair
    hwid = get_hardware_id()
    path = tmp_license_factory(
        priv, hwid, cafe_name="Active Trial", license_type="TRIAL", trial_days=1
    )

    result = check_license(path, pub)

    assert result.ok is True
    assert result.error is None
    assert result.payload["license_type"] == "TRIAL"


# ---------------------------------------------------------------------------
# Case 9: hardware ID idempotent within a process (reboot-stability proxy)
# ---------------------------------------------------------------------------

def test_hardware_id_is_stable_within_process():
    """Within a single process, get_hardware_id() must return the same value.

    True cross-reboot stability is an OS-level property the spike cannot prove
    without a reboot; this asserts the in-process precondition and the report
    lists 'reboot + re-run' as a manual checklist item.
    """
    first = get_hardware_id()
    second = get_hardware_id()

    assert first == second
    assert len(first) == 32  # 32-hex per SDD §16.3


# ---------------------------------------------------------------------------
# Case 10: py-machineid returns non-empty with no admin elevation
# ---------------------------------------------------------------------------

def test_machineid_returns_value_without_admin():
    """The suite itself runs unelevated; this additionally asserts machineid.id()
    returns a non-empty value (proving the no-admin primary path works)."""
    import machineid

    value = machineid.id()

    assert isinstance(value, str)
    assert value.strip() != ""
```

- [ ] **Step 2: Run the full suite and confirm all 10 pass**

Run:
```bash
./backend/venv/Scripts/python.exe -m pytest backend/tests/validation_tasks/arch05/ -v
```
Expected: `10 passed`, listing cases 1–10. Particular attention:
- `test_hardware_mismatch_rejects_foreign_machine PASSED` — the "different machine" proof.
- `test_trial_expired PASSED` and `test_trial_still_valid PASSED` — trial branch both ways.
- `test_machineid_returns_value_without_admin PASSED` — the no-admin proof on Windows.

If `test_trial_expired` fails because `trial_days=-1` produces `today` instead of `yesterday`, the date math in `generate_license` is off by one — confirm `timedelta(days=trial_days)` with a negative argument yields yesterday.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/validation_tasks/arch05/test_arch05.py
git commit -m "test(arch05): cases 6-10 — hardware mismatch, trial both ways, idempotency, no-admin"
```

---

## Task 8: Write the ARCH-05 validation report

**Files:**
- Create: `docs/references/ARCH-05-offline-license-validation.md`

- [ ] **Step 1: Capture the exact runtime evidence first**

Run:
```bash
./backend/venv/Scripts/python.exe -m pytest backend/tests/validation_tasks/arch05/ -v 2>&1 | tee /tmp/arch05_pytest_output.txt
./backend/venv/Scripts/python.exe -c "import nacl, machineid; print('PyNaCl', nacl.__version__); print('py-machineid', machineid.__version__ if hasattr(machineid,'__version__') else 'n/a')"
./backend/venv/Scripts/python.exe -c "import sys; print('python', sys.version)"
./backend/venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'backend/tests/validation_tasks'); from arch05.arch05_lib import get_hardware_id; h=get_hardware_id(); print('hwid_len', len(h)); print('hwid_prefix', h[:8])"
```
Save the captured versions, python version, hwid length (should be 32), and the 10 passed lines. These go verbatim into the report.

- [ ] **Step 2: Write the report**

Create `docs/references/ARCH-05-offline-license-validation.md` with the content below, filling the `<...>` placeholders from Step 1's captured output:

````markdown
# ARCH-05: Ed25519 Offline License Flow Validation

**Status:** ✅ PASS (validated <DATE>, Windows only)
**Validate host:** Windows <WINVER>, Python <PYVER>, PyNaCl <NACLVER>, py-machineid <MIDVER>
**Spike location:** `backend/tests/validation_tasks/arch05/`

This proves the ARCH-05 pass criteria from `TODO.md`: *"Hardware ID is identical across reboots; license verification passes; hardware mismatch is correctly detected."* The full Ed25519 sign → envelope → verify → hardware-bind → trial-expiry flow was exercised end-to-end via a parametrized pytest spike that reimplements SDD §16.3–16.6 in miniature. This is a **validation spike**, not the Phase 1 production module (`backend/licensing/*`) — Phase 1 lifts these functions verbatim once the approach is proven.

---

## 1. Scope: Windows only

| Criterion (from TODO.md) | Validated? | How |
|---|---|---|
| Generate a keypair; sign a test license payload | ✅ | `generate_keypair()` + `generate_license()` (case 1) |
| Verify on a different machine | ✅ (proxied) | Injected foreign hardware ID → `HARDWARE_MISMATCH` (case 6). No second physical machine was available; the cryptographic + comparison logic that would reject a real second machine is identical to what rejects the injected foreign ID. |
| `py-machineid` reboot-stable | ⚠ partial | Idempotent within a process (case 9). True cross-reboot stability is a manual checklist item (§4). |
| `py-machineid` no admin | ✅ Windows | Suite ran unelevated; `machineid.id()` non-empty (case 10). macOS/Linux deferred. |
| Hardware mismatch correctly detected | ✅ | case 6 |

**Deferred (explicit):** macOS and Linux validation of `py-machineid` (reboot-stability + no-admin) are **not** performed in this task and are flagged in `TODO.md`. They should be re-run on each OS before Phase 1 licensing code ships to those platforms.

---

## 2. Summary of the 10 validated cases

All 10 cases pass on Windows, unelevated, no network:

```
<PASTE the 10 "PASSED" lines from /tmp/arch05_pytest_output.txt>
```

| # | Case | Expected | Result |
|---|---|---|---|
| 1 | Round-trip valid license | `ok=True` | ✅ |
| 2 | No `license.key` file | `MISSING` | ✅ |
| 3 | Payload byte tampered after signing | `INVALID_SIGNATURE` | ✅ |
| 4 | Signed with key A, verified with key B | `INVALID_SIGNATURE` | ✅ |
| 5 | Corrupted signature (64 zero bytes) | `INVALID_SIGNATURE` | ✅ |
| 6 | License bound to hwid-A, verified as hwid-B | `HARDWARE_MISMATCH` | ✅ |
| 7 | `TRIAL`, `trial_expires_at` = yesterday | `TRIAL_EXPIRED` | ✅ |
| 8 | `TRIAL`, `trial_expires_at` = tomorrow | `ok=True` | ✅ |
| 9 | `get_hardware_id()` idempotent in-process | two calls identical, len 32 | ✅ |
| 10 | `machineid.id()` non-empty, unelevated | non-empty string | ✅ |

This covers all five `check_license()` outcomes from SDD §16.6 (`MISSING`, `INVALID_SIGNATURE`, `HARDWARE_MISMATCH`, `TRIAL_EXPIRED`, valid) plus three tamper attacks (payload tamper, wrong key, corrupted signature), satisfying FR-LIC-007 and FR-LIC-008's requirement to distinguish "invalid file" from "wrong machine" from "trial expired" from "missing".

---

## 3. Cryptographic scheme proven

- **Algorithm:** Ed25519 (RFC 8032) via PyNaCl `SigningKey` / `VerifyKey`.
- **Signature scope:** canonical JSON of the payload — `json.dumps(payload, sort_keys=True, separators=(",", ":"))` — so formatting differences never cause spurious mismatches. Verified by case 3 (any payload mutation invalidates the signature).
- **Envelope:** `base64(json({"payload": ..., "signature": base64(sig_bytes)}))` per SDD §16.4. Signed, not encrypted (FR-LIC-005).
- **Hardware binding:** payload carries `hardware_id`; `check_license` compares it to `get_hardware_id()` **after** signature verification (SDD §16.6 ordering) — case 4 proves a wrong key is rejected as `INVALID_SIGNATURE`, not as a hardware error.
- **Trial expiry:** `license_type == "TRIAL"` triggers an extra `date.today() > trial_expires_at` check (SDD §16.9). Cases 7 & 8 cover both branches.

---

## 4. Manual checklist before Phase 1 (not automatable in this spike)

- [ ] **Reboot-stability:** reboot this Windows machine, re-run `pytest backend/tests/validation_tasks/arch05/`, and confirm `get_hardware_id()` returns the **same** 32-hex value (capture the current prefix: `<HWID_PREFIX>...`, length 32). The spike proves idempotency within a process only.
- [ ] **macOS:** on a macOS host, run the same suite and confirm cases 9 & 10 pass (reboot-stability + no-admin on Darwin).
- [ ] **Linux:** on a Linux host, run the same suite (note: the fallback fingerprint path in `get_hardware_id` is a stub in this spike; Phase 1 must implement the full SDD §16.3 fallback command set before Linux is considered validated).

---

## 5. Keygen private key custody (R-05)

This spike generates keypairs **ephemerally at runtime** (via `SigningKey.generate()` in fixtures), so **no private key is ever written to disk** and none is committed. The real Phase 1 keygen (`tools/keygen/generate_license.py`) will read a persistent `tools/keygen/private_key.pem` — which is why this task also added the R-05 `.gitignore` patterns (`*.pem`, `*.key`, `private_key*`, `license.key`, `tools/keygen/private_key.pem`) as a precondition. Before Phase 1 issues any real license, a private-key custody policy must be defined per SDD §16.2 / Assumption 9.

---

## 6. Carry-over to Phase 1

The spike's `arch05_lib.py` is structured to be lifted nearly verbatim into the production modules:

| Spike function | Phase 1 destination | Notes |
|---|---|---|
| `get_hardware_id()` | `backend/licensing/fingerprint.py` | Implement the full SDD §16.3 per-OS fallback command set (Windows wmic, macOS system_profiler, Linux dmidecode); the spike's fallback is a stub. Keep the 32-hex SHA-256 output. |
| `LicenseError`, `LicenseResult` | `backend/licensing/verify.py` | Lift verbatim. |
| `check_license()` | `backend/licensing/verify.py` | Lift verbatim; the signature-first → hardware-second ordering is load-bearing (case 4). |
| `generate_keypair()` | (internal keygen only) | Only used in fixtures/tests; Phase 1 keygen runs once out-of-band. |
| `generate_license()` | `tools/keygen/generate_license.py` | Lift verbatim; add CLI args (`--hardware-id`, `--cafe-name`, `--license-type`, `--trial-days`) per Feature 1.2.4. |
| `ARCADE_PUBLIC_KEY_HEX` | `backend/licensing/public_key.py` | The spike passes `public_key_hex` as a param; Phase 1 hardcodes the real public key constant. |

**Decision for Phase 1:** the canonical-JSON signature rule and the base64 envelope from this spike should be reused unchanged — they are validated here and changing them would invalidate the proof.

---

## 7. How to reproduce

```bash
# From the venv (PyNaCl + py-machineid + pytest installed):
./backend/venv/Scripts/python.exe -m pytest backend/tests/validation_tasks/arch05/ -v

# Expected: 10 passed, 0 failed, no network.
```
````

- [ ] **Step 3: Fill every `<...>` placeholder from Step 1's captured output**

No `TBD`/`<...>` may remain. Specifically replace: `<DATE>`, `<WINVER>` (e.g. `11 23H2`), `<PYVER>`, `<NACLVER>`, `<MIDVER>`, the 10 PASSED lines, `<HWID_PREFIX>`.

- [ ] **Step 4: Commit**

```bash
git add docs/references/ARCH-05-offline-license-validation.md
git commit -m "docs(arch-05): offline license flow validation report (Windows)"
```

---

## Task 9: Mark ARCH-05 complete in TODO.md with Windows-only annotation

**Files:**
- Modify: `docs/TODO.md`

- [ ] **Step 1: Read the exact current ARCH-05 block to match text precisely**

Run:
```bash
grep -n "ARCH-05" docs/TODO.md
```
Note the line numbers — the edit must match the current text exactly.

- [ ] **Step 2: Check the box and add the annotation**

In `docs/TODO.md`, change the ARCH-05 line from:
```
- [ ] **ARCH-05: Validate Ed25519 offline license flow end-to-end**
```
to:
```
- [x] **ARCH-05: Validate Ed25519 offline license flow end-to-end** ✅ _(validated Windows only — macOS/Linux deferred; see `references/ARCH-05-offline-license-validation.md`)_
```

- [ ] **Step 3: Verify the edit applied and no other checkboxes changed**

Run:
```bash
grep -n "ARCH-05" docs/TODO.md
```
Expected: the `- [x]` line with the annotation appears once, and the ARCH-04 / ARCH-06 lines remain `- [ ]`. Do a visual confirm that no other `- [ ]`/`- [x]` lines were accidentally touched.

- [ ] **Step 4: Commit**

```bash
git add docs/TODO.md
git commit -m "docs(todo): mark ARCH-05 complete (Windows only)"
```

---

## Task 10: Final verification — clean checkout reproduces the full validation

**Files:** none (verification only)

- [ ] **Step 1: Re-run the full suite from a clean state**

Run:
```bash
./backend/venv/Scripts/python.exe -m pytest backend/tests/validation_tasks/arch05/ -v
```
Expected: `10 passed`, `0 failed`, no warnings about network or missing modules.

- [ ] **Step 2: Confirm no secrets leaked into git history**

Run:
```bash
git log --all --oneline | head -20
git ls-files | grep -iE "\.(pem|key)$|private_key" || echo "CLEAN: no tracked key material"
```
Expected: the recent commits are the ARCH-05 task commits; the second command prints `CLEAN: no tracked key material`.

- [ ] **Step 3: Confirm all deliverables exist**

Run:
```bash
ls backend/tests/validation_tasks/arch05/__init__.py backend/tests/validation_tasks/arch05/arch05_lib.py backend/tests/validation_tasks/arch05/conftest.py backend/tests/validation_tasks/arch05/test_arch05.py docs/references/ARCH-05-offline-license-validation.md
grep -c "\- \[x\] \*\*ARCH-05" docs/TODO.md
```
Expected: all six files listed exist; the grep prints `1` (exactly one checked ARCH-05 line).

- [ ] **Step 4: Report results**

State plainly in the session: "ARCH-05 complete. 10/10 cases pass on Windows, unelevated, no network. Report at `docs/references/ARCH-05-offline-license-validation.md`. macOS/Linux deferred per scope. Next open ARCH task: ARCH-04 (TinyTuya, needs hardware) or ARCH-06 (WebSocket, software-only)." No success claim without the captured output to back it.
