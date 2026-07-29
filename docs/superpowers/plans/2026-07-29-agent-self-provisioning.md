# Agent Self-Provisioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the three remaining items for agent self-provisioning: build-time master PIN injection, HTTP discovery fallback, and wiring the injected master PIN hash into enrollment.

**Architecture:** The backend already has UDP beacon, enroll code generation, and enrollment endpoints. The agent already has UDP discovery, enrollment flow, setup window, config persistence, and master PIN logic. We only need to: (1) inject the master PIN hash at build time instead of runtime `.env`, (2) add HTTP `/api/discovery` fallback when UDP fails, and (3) wire the injected hash into `enroll.ts`.

**Tech Stack:** TypeScript, Electron, Node.js, electron-builder, @node-rs/argon2, vitest

## Global Constraints

- Master PIN plaintext never in source, on disk, or in `.env` — only Argon2id hash baked into binary
- Master PIN hash params: `memoryCost=4096, timeCost=3, parallelism=1` (match `enroll.ts:12-16`)
- HTTP discovery probes common gateways in parallel (max 3 concurrent, 500ms timeout each)
- Enroll code: single-use, 15-min TTL, admin-only generation (already enforced by backend)
- Build script runs before `tsc`; `MASTER_PIN` provided via CI secret or local env var
- All new code covered by unit/integration tests
- Follow existing code style: ES modules, strict TypeScript, existing patterns in `agent/src/main/`

---

### Task 1: Build-Time Master PIN Injection Script

**Files:**
- Create: `agent/scripts/inject-master-pin.js`
- Create: `agent/scripts/inject-master-pin.test.js`
- Modify: `agent/package.json` (add script)
- Modify: `agent/src/main/master-pin.ts` (will be generated, but template exists)

**Interfaces:**
- Consumes: `MASTER_PIN` from process.env (or `--pin` CLI arg)
- Produces: `agent/src/main/master-pin.ts` exporting `MASTER_PIN_HASH: string` and `resolveMasterPinHash(): string`

- [ ] **Step 1.1: Write failing test for inject script**

```javascript
// agent/scripts/inject-master-pin.test.js
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_FILE = path.join(__dirname, '../src/main/master-pin.ts');

describe('inject-master-pin', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(async () => {
    try { await fs.unlink(OUT_FILE); } catch {}
  });

  it('generates master-pin.ts with Argon2id hash from env var', async () => {
    process.env.MASTER_PIN = 'testpin123';
    const { injectMasterPin } = await import('./inject-master-pin.js');
    await injectMasterPin({ pin: 'testpin123', outPath: OUT_FILE });
    const content = await fs.readFile(OUT_FILE, 'utf-8');
    expect(content).toContain('export const MASTER_PIN_HASH = "$argon2id$');
    expect(content).toContain('export function resolveMasterPinHash()');
    expect(content).toContain('return MASTER_PIN_HASH;');
  });

  it('throws if pin is empty', async () => {
    const { injectMasterPin } = await import('./inject-master-pin.js');
    await expect(injectMasterPin({ pin: '', outPath: OUT_FILE })).rejects.toThrow('MASTER_PIN cannot be empty');
  });

  it('uses CLI arg over env var', async () => {
    process.env.MASTER_PIN = 'envpin';
    const { injectMasterPin } = await import('./inject-master-pin.js');
    await injectMasterPin({ pin: 'clipin', outPath: OUT_FILE });
    const content = await fs.readFile(OUT_FILE, 'utf-8');
    expect(content).toContain('clipin'); // hash will be different, but we verify it ran
  });
});
```

- [ ] **Step 1.2: Run test to verify it fails**

```bash
cd agent && npm test -- scripts/inject-master-pin.test.js
```
Expected: FAIL (module not found)

- [ ] **Step 1.3: Implement inject-master-pin.js**

```javascript
// agent/scripts/inject-master-pin.js
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { hash } from '@node-rs/argon2';

const HASH_OPTIONS = {
  memoryCost: 4096,
  timeCost: 3,
  parallelism: 1,
} as const;

/**
 * Generate master-pin.ts with pre-computed Argon2id hash.
 * @param {{ pin?: string; outPath: string }} opts - pin from CLI arg or env; outPath is absolute path to write
 */
export async function injectMasterPin({ pin, outPath }: { pin?: string; outPath: string }): Promise<void> {
  const masterPin = pin ?? process.env.MASTER_PIN;
  if (!masterPin || masterPin.trim() === '') {
    throw new Error('MASTER_PIN cannot be empty. Provide via --pin argument or MASTER_PIN environment variable.');
  }

  const pinHash = await hash(masterPin, HASH_OPTIONS);

  const content = `// agent/src/main/master-pin.ts
// GENERATED AT BUILD TIME — DO NOT EDIT MANUALLY
// Emergency master PIN hash, injected at build time.
// Plaintext PIN is provided via build secret (CI/CD) or local env var.
// Only the Argon2id hash (memoryCost=4096, timeCost=3, parallelism=1) is embedded.

export const MASTER_PIN_HASH = "${pinHash.replace(/"/g, '\\"')}";

/** Returns the pre-computed Argon2id hash of the emergency master PIN. */
export function resolveMasterPinHash(): string {
  return MASTER_PIN_HASH;
}
`;

  await fs.writeFile(outPath, content, 'utf-8');
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const pinArg = args.find(a => a.startsWith('--pin='))?.split('=')[1];
  const outArg = args.find(a => a.startsWith('--out='))?.split('=')[1] ?? 'src/main/master-pin.ts';
  const outPath = path.resolve(outArg);

  try {
    await injectMasterPin({ pin: pinArg, outPath });
    console.log(`[inject-master-pin] Generated ${outPath}`);
  } catch (err) {
    console.error('[inject-master-pin] Failed:', (err as Error).message);
    process.exit(1);
  }
}
```

- [ ] **Step 1.4: Run test to verify it passes**

```bash
cd agent && npm test -- scripts/inject-master-pin.test.js
```
Expected: PASS

- [ ] **Step 1.5: Add build script to package.json**

```json
// agent/package.json (modify scripts section)
{
  "scripts": {
    "inject-master-pin": "node scripts/inject-master-pin.js --pin=$MASTER_PIN --out=src/main/master-pin.ts",
    "build": "npm run inject-master-pin && tsc -p tsconfig.main.json && tsc -p tsconfig.renderer.json && node scripts/copy-renderer-assets.mjs && electron-builder"
  }
}
```

- [ ] **Step 1.6: Commit**

```bash
git add agent/scripts/inject-master-pin.js agent/scripts/inject-master-pin.test.js agent/package.json
git commit -m "feat(agent): add build-time master PIN injection script"
```

---

### Task 2: Update master-pin.ts to Use Injected Hash (Replace Runtime .env Logic)

**Files:**
- Modify: `agent/src/main/master-pin.ts` (replace entire file — will be generated at build time, but we commit a fallback template)
- Modify: `agent/src/main/enroll.ts` (import and use `resolveMasterPinHash`)

**Interfaces:**
- Consumes: `resolveMasterPinHash()` from `./master-pin.js`
- Produces: `master_code_hash` in `LoadedAgentConfig` (written to `agent.config.json`)

- [ ] **Step 2.1: Write failing test for enroll using injected hash**

```typescript
// agent/tests/enroll-injected-hash.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { enrollAgent } from '../src/main/enroll.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TEST_CONFIG = path.join(__dirname, 'test-agent-config.json');

describe('enrollAgent with injected master PIN hash', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(async () => {
    try { await fs.unlink(TEST_CONFIG); } catch {}
  });

  it('writes master_code_hash from injected MASTER_PIN_HASH', async () => {
    // Mock fetch to return successful enrollment
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        seat_id: 'seat_001',
        agent_secret: 'secret123',
        cafe_name: 'Test Cafe',
        override_code_hash: null,
      }),
    }) as any;

    await enrollAgent('ws://localhost:8741', 'ABCD-EFGH', TEST_CONFIG, {
      reconnect_max_seconds: 60,
      health_interval_seconds: 60,
    });

    const config = JSON.parse(await fs.readFile(TEST_CONFIG, 'utf-8'));
    expect(config.master_code_hash).toBeDefined();
    expect(config.master_code_hash).toMatch(/^\$argon2id\$/);
    expect(config.master_code_hash).not.toBeNull();
  });
});
```

- [ ] **Step 2.2: Run test to verify it fails**

```bash
cd agent && npm test -- tests/enroll-injected-hash.test.ts
```
Expected: FAIL (master-pin.ts still uses old .env logic)

- [ ] **Step 2.3: Replace master-pin.ts with generated template (commit a fallback that works without build)**

```typescript
// agent/src/main/master-pin.ts (REPLACE ENTIRE FILE)
// agent/src/main/master-pin.ts
// FALLBACK TEMPLATE — REPLACED AT BUILD TIME by inject-master-pin.js
// Emergency master PIN hash, injected at build time.
// Plaintext PIN is provided via build secret (CI/CD) or local env var.
// Only the Argon2id hash (memoryCost=4096, timeCost=3, parallelism=1) is embedded.

export const MASTER_PIN_HASH = "$argon2id$v=19$m=4096,t=3,p=1$fallback$salt$hash";

/** Returns the pre-computed Argon2id hash of the emergency master PIN. */
export function resolveMasterPinHash(): string {
  return MASTER_PIN_HASH;
}
```

- [ ] **Step 2.4: Update enroll.ts to use resolveMasterPinHash()**

```typescript
// agent/src/main/enroll.ts (modify lines 5-6, 54-55)
// Replace imports
import { saveAgentConfig } from './config/loader.js';
import type { LoadedAgentConfig } from './config/types.js';
import { resolveMasterPinHash } from './master-pin.js';  // CHANGED: was resolveMasterPin

// ... inside enrollAgent function ...

// Replace lines 54-55:
// const masterPin = resolveMasterPin();
// const master_code_hash = masterPin ? await hash(masterPin, MASTER_PIN_HASH_OPTIONS) : null;

// With:
const master_code_hash = resolveMasterPinHash();  // pre-computed at build time
```

- [ ] **Step 2.5: Run test to verify it passes**

```bash
cd agent && npm test -- tests/enroll-injected-hash.test.ts
```
Expected: PASS

- [ ] **Step 2.6: Run existing master-pin tests to ensure no regression**

```bash
cd agent && npm test -- tests/master-pin.test.ts
```
Expected: PASS (tests may need update to match new API)

- [ ] **Step 2.7: Commit**

```bash
git add agent/src/main/master-pin.ts agent/src/main/enroll.ts agent/tests/enroll-injected-hash.test.ts
git commit -m "feat(agent): wire build-time injected master PIN hash into enrollment"
```

---

### Task 3: HTTP `/api/discovery` Fallback in Agent Discovery Client

**Files:**
- Modify: `agent/src/main/discovery.ts`
- Create: `agent/tests/discovery-fallback.test.ts`

**Interfaces:**
- Consumes: `fetch` (global), `COMMON_GATEWAYS` list
- Produces: `string | null` — `ws://host:port` URL or null if all probes fail

- [ ] **Step 3.1: Write failing test for HTTP discovery fallback**

```typescript
// agent/tests/discovery-fallback.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { discoverServer } from '../src/main/discovery.js';

describe('discoverServer HTTP fallback', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    global.fetch = undefined as any;
  });

  it('returns ws URL from HTTP /api/discovery when UDP times out', async () => {
    // Mock UDP to timeout (no message event)
    // Mock fetch to succeed on second gateway
    global.fetch = vi.fn()
      .mockRejectedValueOnce(new Error('network error'))  // 192.168.1.1 fails
      .mockResolvedValueOnce({  // 192.168.0.1 succeeds
        ok: true,
        json: () => Promise.resolve({ host: '192.168.0.100', port: 8741, cafe_name: 'Test' }),
      }) as any;

    const promise = discoverServer(4000);
    // Advance past UDP timeout
    await vi.advanceTimersByTimeAsync(4100);
    const result = await promise;

    expect(result).toBe('ws://192.168.0.100:8741');
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(global.fetch).toHaveBeenCalledWith('http://192.168.1.1/api/discovery', expect.any(Object));
    expect(global.fetch).toHaveBeenCalledWith('http://192.168.0.1/api/discovery', expect.any(Object));
  });

  it('returns null when all HTTP probes fail', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('network error')) as any;

    const promise = discoverServer(4000);
    await vi.advanceTimersByTimeAsync(4100);
    const result = await promise;

    expect(result).toBeNull();
  });

  it('probes max 3 gateways concurrently', async () => {
    let concurrent = 0;
    let maxConcurrent = 0;
    global.fetch = vi.fn(() => {
      concurrent++;
      maxConcurrent = Math.max(maxConcurrent, concurrent);
      return new Promise(resolve => setTimeout(() => {
        concurrent--;
        resolve({ ok: false, status: 500 });
      }, 100));
    }) as any;

    const promise = discoverServer(4000);
    await vi.advanceTimersByTimeAsync(4100);
    await promise;

    expect(maxConcurrent).toBeLessThanOrEqual(3);
  });
});
```

- [ ] **Step 3.2: Run test to verify it fails**

```bash
cd agent && npm test -- tests/discovery-fallback.test.ts
```
Expected: FAIL (discovery.ts has no HTTP fallback)

- [ ] **Step 3.3: Implement HTTP fallback in discovery.ts**

```typescript
// agent/src/main/discovery.ts (REPLACE discoverServer function, keep beaconToWsUrl)
/**
 * Discover the Arcade server on the LAN.
 *
 * 1) Try UDP broadcast beacon (4s timeout)
 * 2) Fallback: probe common LAN gateways via HTTP GET /api/discovery
 *    (parallel, max 3 concurrent, 500ms timeout each)
 *
 * @param timeoutMs How long to wait for UDP beacon before fallback.
 * @returns A `ws://host:port` URL, or null if no server discovered.
 */
export async function discoverServer(timeoutMs = 4000): Promise<string | null> {
  // 1) Try UDP broadcast beacon.
  const udp = await new Promise<string | null>((resolve) => {
    const sock = dgram.createSocket('udp4');
    let done = false;
    const finish = (url: string | null) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      sock.close();
      resolve(url);
    };
    const timer = setTimeout(() => finish(null), timeoutMs);
    sock.on('message', (msg: Buffer) => finish(beaconToWsUrl(msg.toString())));
    sock.on('error', () => finish(null));
    sock.bind(BEACON_PORT);
  });
  if (udp) return udp;

  // 2) Fallback: probe common LAN gateways via HTTP /api/discovery.
  const COMMON_GATEWAYS = [
    '192.168.1.1', '192.168.0.1', '192.168.1.254', '192.168.0.254',
    '10.0.0.1', '10.0.1.1', '10.1.1.1',
    '172.16.0.1', '172.16.1.1',
  ];

  const PROBE_TIMEOUT_MS = 500;
  const MAX_CONCURRENT = 3;

  async function probeGateway(ip: string): Promise<string | null> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
    try {
      const res = await fetch(`http://${ip}/api/discovery`, {
        signal: controller.signal,
        headers: { Accept: 'application/json' },
      });
      clearTimeout(timeout);
      if (!res.ok) return null;
      const data = await res.json() as { host: string; port: number };
      return `ws://${data.host}:${data.port}`;
    } catch {
      clearTimeout(timeout);
      return null;
    }
  }

  // Run probes in batches of MAX_CONCURRENT
  for (let i = 0; i < COMMON_GATEWAYS.length; i += MAX_CONCURRENT) {
    const batch = COMMON_GATEWAYS.slice(i, i + MAX_CONCURRENT);
    const results = await Promise.all(batch.map(probeGateway));
    const success = results.find(r => r !== null);
    if (success) return success;
  }

  return null;
}
```

- [ ] **Step 3.4: Run test to verify it passes**

```bash
cd agent && npm test -- tests/discovery-fallback.test.ts
```
Expected: PASS

- [ ] **Step 3.5: Run existing discovery tests**

```bash
cd agent && npm test -- tests/enroll.test.ts
```
Expected: PASS (enroll tests use discoverServer)

- [ ] **Step 3.6: Commit**

```bash
git add agent/src/main/discovery.ts agent/tests/discovery-fallback.test.ts
git commit -m "feat(agent): add HTTP /api/discovery fallback for agent self-provisioning"
```

---

### Task 4: Integration Test & Documentation Update

**Files:**
- Modify: `agent/tests/enroll.test.ts` (ensure full flow works with injected hash + HTTP fallback)
- Modify: `docs/agent-setup.md` (if any user-facing changes)

**Interfaces:**
- Full end-to-end: first run → discover → enroll → write config → relaunch

- [ ] **Step 4.1: Run full agent test suite**

```bash
cd agent && npm test
```
Expected: All tests pass

- [ ] **Step 4.2: Build agent to verify build pipeline**

```bash
cd agent && MASTER_PIN=1234 npm run build
```
Expected: Build succeeds, `dist/main/master-pin.js` contains injected hash

- [ ] **Step 4.3: Verify generated master-pin.js in dist**

```bash
cat agent/dist/main/master-pin.js
```
Expected: Contains `MASTER_PIN_HASH = "$argon2id$..."` not fallback

- [ ] **Step 4.4: Update docs/agent-setup.md if needed**

Check if any user-facing instructions changed (likely not — self-provisioning is already documented)

- [ ] **Step 4.5: Commit any doc changes**

```bash
git add docs/agent-setup.md
git commit -m "docs(agent): update self-provisioning docs if needed"
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|------------------|------|
| Build-time master PIN injection (esbuild/Vite define) | Task 1 |
| Generated master-pin.ts exports pre-computed Argon2id hash | Task 1, 2 |
| enroll.ts uses injected hash (no runtime .env) | Task 2 |
| HTTP /api/discovery fallback probes common gateways | Task 3 |
| Max 3 concurrent probes, 500ms timeout each | Task 3 |
| Master PIN only works offline (already in ws/client.ts) | Verified existing |
| Enroll code single-use, 15-min TTL, admin-only (backend) | Backend already done |
| Ctrl+Shift+O opens override dialog; Settings re-opens setup | Already implemented |

---

## Execution Order

1. Task 1: Build script + tests
2. Task 2: Wire injected hash into enrollment
3. Task 3: HTTP discovery fallback
4. Task 4: Integration test + build verification

---

**Plan complete and saved to `docs/superpowers/plans/2026-07-29-agent-self-provisioning.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints for review

**Which approach?**
