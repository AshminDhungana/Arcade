import { test, expect, VIEWPORTS } from './fixtures';

test.describe('Modal close button tap target', () => {
  for (const width of VIEWPORTS) {
    test(`Create Member modal close >= 44px at ${width}px`, async ({ authenticatedPage }) => {
      await authenticatedPage.setViewportSize({ width, height: 800 });

      // NOTE: auth state is in-memory only (src/store/authStore.ts has no persist
      // middleware), so a full `page.goto('/members')` reload wipes the session and
      // ProtectedRoute bounces back to /login. Navigate client-side from the
      // dashboard to keep the SPA session alive. The fixture's login() already lands
      // us on the authenticated dashboard ('/').
      if (width < 768) {
        await authenticatedPage.getByRole('button', { name: /open menu/i }).click();
        await authenticatedPage.getByRole('link', { name: /members/i }).last().click();
      } else {
        await authenticatedPage.getByRole('link', { name: /members/i }).click();
      }

      await expect(authenticatedPage.getByRole('heading', { name: /members/i })).toBeVisible();
      await authenticatedPage.getByRole('button', { name: /new member/i }).click();

      const close = authenticatedPage.getByRole('dialog').getByRole('button', { name: /close/i });
      await expect(close).toBeVisible();
      const box = await close.boundingBox();
      expect(box?.height).toBeGreaterThanOrEqual(44);
      expect(box?.width).toBeGreaterThanOrEqual(44);
    });
  }
});
