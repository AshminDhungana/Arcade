import { test, expect, VIEWPORTS } from './fixtures';
import { expectNoHorizontalOverflow } from './support/assertions';

test.describe('NavShell responsive', () => {
  for (const width of VIEWPORTS) {
    test(`no horizontal overflow at ${width}px`, async ({ authenticatedPage }) => {
      await authenticatedPage.setViewportSize({ width, height: 800 });
      await expectNoHorizontalOverflow(authenticatedPage, `navshell ${width}px`);
    });
  }

  test('mobile (<md): sidebar hidden, hamburger visible', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize({ width: 375, height: 800 });
    await expect(authenticatedPage.locator('aside').first()).toBeHidden();
    await expect(authenticatedPage.getByRole('button', { name: /open menu/i })).toBeVisible();
  });

  test('tablet (≥md): persistent sidebar visible', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize({ width: 768, height: 800 });
    await expect(authenticatedPage.locator('aside').first()).toBeVisible();
  });

  test('hamburger opens and closes the drawer', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize({ width: 375, height: 800 });
    await authenticatedPage.getByRole('button', { name: /open menu/i }).click();
    await expect(authenticatedPage.getByRole('button', { name: /close menu/i })).toBeVisible();
    await authenticatedPage.getByRole('button', { name: /close menu/i }).click();
    await expect(authenticatedPage.getByRole('button', { name: /close menu/i })).toBeHidden();
  });

  test('mobile menu button is a 44px tap target', async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize({ width: 375, height: 800 });
    const box = await authenticatedPage.getByRole('button', { name: /open menu/i }).boundingBox();
    expect(box?.height).toBeGreaterThanOrEqual(44);
    expect(box?.width).toBeGreaterThanOrEqual(44);
  });
});
