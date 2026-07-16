import { test, expect, VIEWPORTS } from './fixtures';

test.describe('Table scrolls instead of clipping', () => {
  for (const width of VIEWPORTS) {
    test(`members table wrapper is overflow-x:auto at ${width}px`, async ({ authenticatedPage }) => {
      await authenticatedPage.setViewportSize({ width, height: 800 });

      // NOTE: auth state is in-memory only (src/store/authStore.ts has no persist
      // middleware), so a full `page.goto('/members')` reload wipes the session and
      // ProtectedRoute bounces back to /login. Navigate client-side via the Members
      // nav link to keep the SPA session alive. The fixture's login() already lands
      // us on the authenticated dashboard ('/').
      if (width < 768) {
        await authenticatedPage.getByRole('button', { name: /open menu/i }).click();
        await authenticatedPage.getByRole('link', { name: /members/i }).last().click();
      } else {
        await authenticatedPage.getByRole('link', { name: /members/i }).click();
      }

      await expect(authenticatedPage.getByRole('heading', { name: /members/i })).toBeVisible();

      const wrapper = authenticatedPage.getByRole('table').locator('xpath=..');
      await expect(wrapper).toHaveCSS('overflow-x', 'auto');
    });
  }
});
