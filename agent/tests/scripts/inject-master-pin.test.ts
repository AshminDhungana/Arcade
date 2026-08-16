/**
 * Tests for inject-master-pin.js
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_FILE = path.join(__dirname, '../../src/main/master-pin.ts');

async function runInjectScript(pin: string, outPath: string): Promise<{ stdout: string; stderr: string; code: number }> {
  const { spawn } = await import('node:child_process');
  const scriptPath = path.join(__dirname, '../../scripts/inject-master-pin.js');

  return new Promise((resolve) => {
    const child = spawn('node', [scriptPath, `--pin=${pin}`, `--out=${outPath}`], {
      cwd: path.join(__dirname, '../..'),
      env: { ...process.env, MASTER_PIN: '' },
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (data) => { stdout += data.toString(); });
    child.stderr.on('data', (data) => { stderr += data.toString(); });

    child.on('close', (code) => {
      resolve({ stdout, stderr, code: code ?? 0 });
    });
  });
}

describe('inject-master-pin.js', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(async () => {
    try { await fs.unlink(OUT_FILE); } catch {}
  });

  it('generates master-pin.ts with Argon2id hash from CLI arg', async () => {
    const result = await runInjectScript('testpin123', 'src/main/master-pin.ts');

    expect(result.code).toBe(0);
    expect(result.stdout).toContain('Generated src/main/master-pin.ts');

    const content = await fs.readFile(OUT_FILE, 'utf-8');
    expect(content).toContain('export const MASTER_PIN_HASH = "$argon2id$');
    expect(content).toContain('export function resolveMasterPinHash()');
    expect(content).toContain('return MASTER_PIN_HASH;');
    expect(content).not.toContain('testpin123');
  }, 60000);

  it('generates master-pin.ts with Argon2id hash from env var', async () => {
    const { spawn } = await import('node:child_process');
    const scriptPath = path.join(__dirname, '../../scripts/inject-master-pin.js');

    return new Promise<void>((resolve) => {
      const child = spawn('node', [scriptPath, `--out=src/main/master-pin.ts`], {
        cwd: path.join(__dirname, '../..'),
        env: { ...process.env, MASTER_PIN: 'envpin456' },
      });

      let stdout = '';
      child.stdout.on('data', (data) => { stdout += data.toString(); });
      child.on('close', async (code) => {
        expect(code).toBe(0);
        const content = await fs.readFile(OUT_FILE, 'utf-8');
        expect(content).toContain('export const MASTER_PIN_HASH = "$argon2id$');
        resolve();
      });
    });
  });

  it('exits with error code when PIN is empty', async () => {
    const result = await runInjectScript('', 'src/main/master-pin.ts');
    expect(result.code).not.toBe(0);
  });

  it('exits with error code when --out is missing', async () => {
    const { spawn } = await import('node:child_process');
    const scriptPath = path.join(__dirname, '../../scripts/inject-master-pin.js');

    return new Promise<void>((resolve) => {
      const child = spawn('node', [scriptPath, `--pin=testpin`], {
        cwd: path.join(__dirname, '../..'),
      });
      child.on('close', (code) => {
        expect(code).not.toBe(0);
        resolve();
      });
    });
  });

  it('produces different hashes for different PINs', async () => {
    const file1 = path.join(__dirname, '../../src/main/master-pin-1.ts');
    const file2 = path.join(__dirname, '../../src/main/master-pin-2.ts');

    try {
      await runInjectScript('pin111', 'src/main/master-pin-1.ts');
      await runInjectScript('pin222', 'src/main/master-pin-2.ts');

      const content1 = await fs.readFile(file1, 'utf-8');
      const content2 = await fs.readFile(file2, 'utf-8');

      const regex = /MASTER_PIN_HASH = "(\$argon2id\$[^"]+)"/;
      const match1 = content1.match(regex);
      const match2 = content2.match(regex);
      const hash1 = match1 ? match1[1] : undefined;
      const hash2 = match2 ? match2[1] : undefined;

      expect(hash1).toBeDefined();
      expect(hash2).toBeDefined();
      expect(hash1).not.toBe(hash2);
    } finally {
      try { await fs.unlink(file1); } catch {}
      try { await fs.unlink(file2); } catch {}
    }
  });
});
