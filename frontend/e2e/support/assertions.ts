import { type Page, expect } from '@playwright/test';

/** True if the document is wider than the viewport (horizontal scroll present). */
export async function expectNoHorizontalOverflow(page: Page, label: string): Promise<void> {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, `horizontal overflow detected on ${label}`).toBeLessThanOrEqual(0);
}

/**
 * Assert every matched VISIBLE interactive control is at least 44x44px (SDD §6.6).
 * Hidden (display:none) controls report a 0x0 box and are not tappable, so they
 * are skipped — otherwise responsive layouts (e.g. the `md:hidden` hamburger vs the
 * `hidden md:flex` sidebar links) would false-fail a bare `button` scan at any width.
 */
export async function expectTapTargets(page: Page, selector: string, label: string): Promise<void> {
  const boxes = await page.$$eval(selector, (els) =>
    els
      .map((el) => {
        const r = el.getBoundingClientRect();
        return { w: Math.round(r.width), h: Math.round(r.height), tag: el.tagName };
      })
      .filter((b) => b.w > 0 && b.h > 0),
  );
  expect(boxes.length, `${label}: no visible elements matched "${selector}"`).toBeGreaterThan(0);
  for (const b of boxes) {
    expect(b.h, `${label}: ${b.tag} tap-target height ${b.h}px < 44`).toBeGreaterThanOrEqual(44);
    expect(b.w, `${label}: ${b.tag} tap-target width ${b.w}px < 44`).toBeGreaterThanOrEqual(44);
  }
}
