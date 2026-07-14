/**
 * Publish static renderer assets (index.html, kiosk.css, hud.html, hud.css)
 * into dist/renderer after the TypeScript build.
 *
 * Dependency-free: uses Node's built-in fs.cpSync. Run after the two `tsc`
 * calls in the `build`/`start` npm scripts.
 */

import fs from 'node:fs';

fs.cpSync('src/renderer', 'dist/renderer', {
  recursive: true,
  filter: (s) => {
    // Allow directories through so traversal continues; copy only .html/.css.
    if (fs.statSync(s).isDirectory()) return true;
    return s.endsWith('.html') || s.endsWith('.css');
  },
});

console.log('[copy-renderer-assets] Published *.html / *.css to dist/renderer');
