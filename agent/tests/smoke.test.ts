// agent/tests/smoke.test.ts
import { describe, it, expect, vi } from 'vitest'
import { spawn } from 'child_process'
import path from 'path'
import { fileURLToPath } from 'node:url'
import fs from 'fs'

const __dirname = fileURLToPath(new URL('.', import.meta.url))

describe('Agent smoke test', () => {
  it('should exit with code 0 when --smoke-test flag is passed', async () => {
    const distPath = path.resolve(__dirname, '../dist/main/index.js')

    // Skip if dist doesn't exist (requires build first)
    if (!fs.existsSync(distPath)) {
      vi.skip('dist not built - run npm run build first')
      return
    }

    const proc = spawn('node', [
      distPath,
      '--smoke-test'
    ], {
      cwd: path.resolve(__dirname, '..'),
      timeout: 30000
    })

    await new Promise<void>((resolve, reject) => {
      proc.on('exit', (code) => {
        expect(code).toBe(0)
        resolve()
      })
      proc.on('error', reject)
    })
  })
})
