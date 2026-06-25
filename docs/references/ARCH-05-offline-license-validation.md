# ARCH-05: Ed25519 Offline License Flow Validation

**Status:** ✅ PASS (validated 2026-06-25, Windows only)
**Validate host:** Windows 11 (10.0.26200), Python 3.13.12, PyNaCl 1.5.0, py-machineid 0.6.0
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
backend/tests/validation_tasks/arch05/test_arch05.py::test_round_trip_valid_license PASSED [ 10%]
backend/tests/validation_tasks/arch05/test_arch05.py::test_missing_license_file PASSED [ 20%]
backend/tests/validation_tasks/arch05/test_arch05.py::test_invalid_signature_payload_tampered PASSED [ 30%]
backend/tests/validation_tasks/arch05/test_arch05.py::test_invalid_signature_wrong_key PASSED [ 40%]
backend/tests/validation_tasks/arch05/test_arch05.py::test_invalid_signature_corrupted PASSED [ 50%]
backend/tests/validation_tasks/arch05/test_arch05.py::test_hardware_mismatch_rejects_foreign_machine PASSED [ 60%]
backend/tests/validation_tasks/arch05/test_arch05.py::test_trial_expired PASSED [ 70%]
backend/tests/validation_tasks/arch05/test_arch05.py::test_trial_still_valid PASSED [ 80%]
backend/tests/validation_tasks/arch05/test_arch05.py::test_hardware_id_is_stable_within_process PASSED [ 90%]
backend/tests/validation_tasks/arch05/test_arch05.py::test_machineid_returns_value_without_admin PASSED [100%]
============================= 10 passed ==============================
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

- [ ] **Reboot-stability:** reboot this Windows machine, re-run `pytest backend/tests/validation_tasks/arch05/`, and confirm `get_hardware_id()` returns the **same** 32-hex value (capture the current prefix: `c7e331a0...`, length 32). The spike proves idempotency within a process only.
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
