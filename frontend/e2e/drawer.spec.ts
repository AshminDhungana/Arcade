import { test, expect, VIEWPORTS } from './fixtures';

test.describe('SessionDrawer', () => {
  for (const width of VIEWPORTS) {
    test(`drawer close >= 44px, no overflow at ${width}px`, async ({ authenticatedPage }) => {
      await authenticatedPage.setViewportSize({ width, height: 800 });
      await authenticatedPage.getByRole('button', { name: /PC-03/i }).click();
      const dialog = authenticatedPage.getByRole('dialog');
      await expect(dialog).toBeVisible();
      const close = dialog.getByRole('button', { name: /close drawer/i });
      const box = await close.boundingBox();
      // Round: the button is exactly w-11 (44px); sub-pixel layout rounding
      // (e.g. 43.99997) must not fail the >= 44px tap-target requirement.
      expect(Math.round(box?.height ?? 0)).toBeGreaterThanOrEqual(44);
      expect(Math.round(box?.width ?? 0)).toBeGreaterThanOrEqual(44);
      const overflow = await authenticatedPage.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, `drawer overflow at ${width}px`).toBeLessThanOrEqual(0);
    });
  }

  for (const width of VIEWPORTS) {
    test(`seat action modal controls >= 44px at ${width}px`, async ({ authenticatedPage }) => {
      await authenticatedPage.setViewportSize({ width, height: 800 });
      await authenticatedPage.getByRole('button', { name: /PC-01/i }).click();
      const dialog = authenticatedPage.getByRole('dialog');
      await expect(dialog).toBeVisible();
      const close = dialog.getByRole('button', { name: /close modal/i });
      const cb = await close.boundingBox();
      expect(Math.round(cb?.height ?? 0)).toBeGreaterThanOrEqual(44);
      expect(Math.round(cb?.width ?? 0)).toBeGreaterThanOrEqual(44);
      for (const b of await dialog.getByRole('button').elementHandles()) {
        const box = await b.boundingBox();
        expect(Math.round(box?.height ?? 0), 'action button height').toBeGreaterThanOrEqual(44);
      }
    });
  }
});
