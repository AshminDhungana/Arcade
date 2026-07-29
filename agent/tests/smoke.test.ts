// agent/tests/smoke.test.ts
import { describe, it, expect } from 'vitest'
import { spawn } from 'child_process'
import path from 'path'

describe('Agent smoke test', () => {
  it('should exit with code 0 when --smoke-test flag is passed', async () => {
    const proc = spawn('node', [
      path.resolve('dist/main/index.js'),
      '--smoke-test'
    ], {
      cwd: path.resolve('agent'),
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
