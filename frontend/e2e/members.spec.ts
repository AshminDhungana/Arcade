import { test, expect, VIEWPORTS } from './fixtures';
import { expectNoHorizontalOverflow, expectTapTargets } from './support/assertions';

test.describe('Members page', () => {
  for (const width of VIEWPORTS) {
    test(`no overflow + tap targets at ${width}px`, async ({ authenticatedPage }) => {
      await authenticatedPage.setViewportSize({ width, height: 800 });

      // NOTE: auth state is in-memory only (src/store/authStore.ts has no persist
      // middleware), so a full `page.goto('/members')` reload wipes the session and
      // ProtectedRoute bounces back to /login. Navigate client-side to keep the SPA
      // session alive. The fixture's login() already lands us on '/'.
      if (width < 768) {
        await authenticatedPage.getByRole('button', { name: /open menu/i }).click();
        await authenticatedPage.getByRole('link', { name: /members/i }).last().click();
      } else {
        await authenticatedPage.getByRole('link', { name: /members/i }).click();
      }

      await expect(authenticatedPage.getByRole('heading', { name: /members/i })).toBeVisible();
      await expectNoHorizontalOverflow(authenticatedPage, `members ${width}px`);
      await expectTapTargets(authenticatedPage, 'button', `members buttons @ ${width}px`);

      // Stacking guard: header must be a vertical column below `sm` (640px) and a
      // row at sm+. The overflow check alone does NOT catch a revert to the old
      // single-row header, because flex children shrink to fit.
      const expectedDir = width < 640 ? 'column' : 'row';
      const flexDir = await authenticatedPage
        .getByTestId('members-header')
        .evaluate((el) => getComputedStyle(el).flexDirection);
      expect(flexDir, `members header flex-direction @ ${width}px`).toBe(expectedDir);
    });
  }
});
