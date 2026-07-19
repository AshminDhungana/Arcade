// tools/keygen/icon/render_logo.mjs
// Dev-only asset build. Run from this dir:  node render_logo.mjs
// Rasterizes arcade_icon.svg into the PNGs the GUI loads at runtime.
// Requires: npm install sharp   (NOT a runtime dependency of the tool)
import sharp from 'sharp';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const dir = fileURLToPath(new URL('./', import.meta.url));
const svg = readFileSync(resolve(dir, 'arcade_icon.svg'));
const gradSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="3">`
  + `<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0">`
  + `<stop offset="0%" stop-color="#0334F0"/>`
  + `<stop offset="100%" stop-color="#06A3FC"/></linearGradient></defs>`
  + `<rect width="300" height="3" fill="url(#g)"/></svg>`;

await sharp(svg, { density: 384 }).resize(64, 64).png().toFile(resolve(dir, 'arcade_logo_64.png'));
await sharp(svg, { density: 384 }).resize(128, 128).png().toFile(resolve(dir, 'arcade_logo_128.png'));
await sharp(Buffer.from(gradSvg)).png().toFile(resolve(dir, 'arcade_gradient_3px.png'));
console.log('logo assets written');
