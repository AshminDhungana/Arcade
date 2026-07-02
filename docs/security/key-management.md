# Arcade Security - Key Management

> Last updated: 2026-07-02 (Phase 1, in progress)
> See also: `docs/PRODUCT_BRIEF.md`, `backend/licensing/verify.py`, `tools/keygen/`

This document defines the lifecycle of the Ed25519 keypair, private key custody rules, and the offline license signing/verification flow.

## Key Generation

### Generate the Ed25519 keypair (one-time setup)

```bash
python tools/keygen/generate_keys.py
```

This produces:
- `tools/keygen/private_key.pem` — **Secret** — Ed25519 private key hex (never commit, never distribute)
- `backend/licensing/public_key.py` — **Public** — Ed25519 public key hex, embedded into the application

**File locations:**
- `tools/keygen/private_key.pem` — Gitignored. Only ever exists on the signing machine.
- `backend/licensing/public_key.py` — Committed to the repo. This is what ships with the application.

## Private Key Custody Policy

The Ed25519 private key (`tools/keygen/private_key.pem`) is the single most sensitive asset in Arcade. Compromise allows unlimited license generation.

### Rules

1. **Never commit** — The file is in `.gitignore`. CI should fail if any `.pem` or `private_key*` is detected in the repository.
2. **Minimal access** — Only the build/release engineer has access to the signing machine.
3. **No cloud storage** — Do not store the key in cloud drives (Dropbox, Google Drive, etc.).
4. **Hardware-backed storage** — Prefer a hardware token or encrypted USB drive for cold storage.
5. **Audit all usage** — Every `generate_license.py` invocation is logged with the target hardware ID and cafe name.

### CI Protection

The `.github/workflows/ci.yml` should include a step that checks for any `.pem` or `private_key*` file in git history. If found, the build fails.

## License Generation

### Generate a new license

```bash
python -m tools.keygen.generate_license \
    --hardware-id <hwid> \
    --cafe-name "Galaxy Gaming Lounge" \
    --license-type PERPETUAL
```

**Flags:**
- `--hardware-id`: Target machine's hardware ID (from `py-machineid` or `fingerprint.py` — 32-char hex)
- `--cafe-name`: Name displayed in the launcher after verification
- `--license-type`: `PERPETUAL` or `TRIAL`
- `--trial-days`: Only for TRIAL (default: `30`)

Output: `license.key` (base64-encoded signed JSON payload)

### Hardware ID extraction

On the target machine (the counter PC):

```bash
python -c "from backend.licensing.fingerprint import get_hardware_id; print(get_hardware_id())"
```

No admin privileges are required on any OS. Both `py-machineid` and OS-specific fallbacks (`wmic`, `system_profiler`, `dmidecode`) are used.

## License Verification Flow

When `launcher.py` starts (or on every server start for `make backend-dev`):

1. Reads `license.key` from the app root directory.
2. Base64-decodes the envelope.
3. Verifies the Ed25519 signature against `ARCADE_PUBLIC_KEY_HEX`.
4. Compares the `hardware_id` in the payload with `get_hardware_id()`.
5. If `TRIAL`, checks `trial_expires_at > today`.
6. If all checks pass, the launcher unlocks the setup wizard or starts the server.
7. If any check fails, the launcher shows the **Activation Screen** with the specific error (MISSING, INVALID_SIGNATURE, HARDWARE_MISMATCH, or TRIAL_EXPIRED).

## License File Lifecycle

```text
+---------------+     +---------------+     +---------------+
|  Keypair      |}else--> |  Sign license | --> |  Install/key  |
|  Generation   |     |  (generate_)  |     |  file (license)|
+---------------+     +---------------+     +---------------+
        |                     |                     |
        v                     v                     v
   pyNaCl signing      tools/keygen/          Place at app root
   (SigningKey)        generate_license.py    license.key
```

1. **Generation** (`generate_keys.py`): Create keypair once. Store private key securely.
2. **Signing** (`generate_license.py`): Use hardware ID from the target machine. Sign and produce `license.key`.
3. **Distribution**: Transfer only the `license.key` file to the customer. Never distribute the private key.
4. **Installation**: Customer places `license.key` in the app root directory.
5. **Verification**: Launcher/server checks `license.key` on every start. No internet required.

## Security Considerations

- **Offline-first**: License verification is entirely local. No license server, no phone home, no cloud dependency.
- **Tamper-proof**: Modifying `license.key` invalidates the signature. The file cannot be cloned to another machine because the hardware ID is embedded in the signed payload.
- **Key rotation**: To rotate keys, generate a new keypair, update `public_key.py`, rebuild the application, and re-sign all existing licenses.
- **Hardware changes**: If a significant hardware change occurs (e.g., motherboard replacement), the hardware ID may change. The operator must contact the seller with the new hardware ID to receive a reissued license. This is a manual process.
