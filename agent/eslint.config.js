// ESLint flat config (ESLint 9 dropped the legacy .eslintrc.json format the
// plan was written against). This mirrors the plan's Task 7 intent for the
// Electron main process: parser @typescript-eslint/parser,
// eslint:recommended, @typescript-eslint/recommended, prettier compat,
// no-unused-vars (warn, argsIgnorePattern ^_).
import js from '@eslint/js';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import tsParser from '@typescript-eslint/parser';
import prettier from 'eslint-config-prettier';
import globals from 'globals';

export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  js.configs.recommended,
  {
    files: ['src/**/*.ts'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: 'module',
      },
      // Node + Electron main-process globals (require, module, process, ...).
      // WebSocket and CloseEvent are available natively in Node.js 22+.
      globals: { ...globals.node, ...globals.commonjs, WebSocket: 'readonly', CloseEvent: 'readonly' },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'no-unused-vars': 'off', // handled by @typescript-eslint rule
    },
  },
  prettier,
];
