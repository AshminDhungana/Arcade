import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
  },
  resolve: {
    alias: {
      './master-pin.js': resolve(__dirname, 'src/main/master-pin.js'),
      '../src/main/master-pin.js': resolve(__dirname, 'src/main/master-pin.js'),
      './config/loader.js': resolve(__dirname, 'src/main/config/loader.ts'),
      '../src/main/config/loader.js': resolve(__dirname, 'src/main/config/loader.ts'),
    },
  },
});
