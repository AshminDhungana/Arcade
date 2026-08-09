// agent/tests/smoke.test.ts
import { describe, it, expect, vi } from 'vitest'
import { spawn } from 'child_process'
import path from 'path'
import fs from 'fs'

// NOTE: the vitest jsdom environment mangles `import.meta.url`, so resolve
// paths from the process CWD (vitest runs from the agent package root).
const projectRoot = process.cwd()

describe('Agent smoke test', () => {
  it('should exit with code 0 when --smoke-test flag is passed', async () => {
    const distPath = path.resolve(projectRoot, 'dist/main/index.js')

    // Skip if dist doesn't exist (requires build first)
    if (!fs.existsSync(distPath)) {
      vi.skip('dist not built - run npm run build first')
      return
    }

    const proc = spawn('node', [
      distPath,
      '--smoke-test'
    ], {
      cwd: projectRoot,
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
