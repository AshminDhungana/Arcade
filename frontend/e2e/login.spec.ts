import { test, expect, VIEWPORTS, mockApi } from './fixtures';
import { expectNoHorizontalOverflow, expectTapTargets } from './support/assertions';

test.describe('Login page', () => {
  for (const width of VIEWPORTS) {
    test(`no overflow + tap targets at ${width}px`, async ({ page }) => {
      await mockApi(page);
      await page.setViewportSize({ width, height: 800 });
      await page.goto('/login');
      await expect(page.getByRole('heading', { name: /staff sign in/i })).toBeVisible();
      // Logo is now above the card, so check for it separately
      await expect(page.getByRole('button', { name: /toggle theme \(logo\)/i })).toBeVisible();
      await expectNoHorizontalOverflow(page, `login ${width}px`);
      // inputs + sign-in + pin toggle
      await expectTapTargets(page, 'input, button', `login controls @ ${width}px`);
    });
  }
});
