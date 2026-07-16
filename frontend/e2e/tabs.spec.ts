import { test, expect, VIEWPORTS } from './fixtures';

test.describe('Tabs strip does not overflow', () => {
  for (const width of VIEWPORTS) {
    test(`settings tabs scroll, no overflow at ${width}px`, async ({ authenticatedPage }) => {
      await authenticatedPage.setViewportSize({ width, height: 800 });

      // NOTE: auth state is in-memory only (src/store/authStore.ts has no persist
      // middleware), so a full `page.goto('/settings')` reload wipes the session and
      // ProtectedRoute bounces back to /login. Navigate client-side to keep the SPA
      // session alive. The fixture's login() already lands us on the dashboard ('/').
      if (width < 768) {
        await authenticatedPage.getByRole('button', { name: /open menu/i }).click();
        await authenticatedPage.getByRole('link', { name: /settings/i }).last().click();
      } else {
        await authenticatedPage.getByRole('link', { name: /settings/i }).click();
      }

      const tablist = authenticatedPage.getByRole('tablist');
      await expect(tablist).toHaveCSS('overflow-x', 'auto');
      const overflow = await authenticatedPage.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, `tabs overflow at ${width}px`).toBeLessThanOrEqual(0);
    });
  }
});
