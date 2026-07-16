import { test, expect, VIEWPORTS } from './fixtures';
import { expectTapTargets } from './support/assertions';

test.describe('Button tap targets', () => {
  for (const width of VIEWPORTS) {
    test(`Buttons >= 44px at ${width}px (Members)`, async ({ authenticatedPage }) => {
      await authenticatedPage.setViewportSize({ width, height: 800 });

      // NOTE: auth state is in-memory only (src/store/authStore.ts has no
      // persist middleware), so a full `page.goto('/members')` reload wipes the
      // session and ProtectedRoute bounces back to /login. Navigate client-side
      // via the Members nav link to keep the SPA session alive. The fixture's
      // login() already lands us on the authenticated dashboard ('/').
      if (width < 768) {
        await authenticatedPage.getByRole('button', { name: /open menu/i }).click();
        await authenticatedPage.getByRole('link', { name: /^members$/i }).last().click();
      } else {
        await authenticatedPage.getByRole('link', { name: /^members$/i }).click();
      }

      await expect(authenticatedPage.getByRole('heading', { name: /members/i })).toBeVisible();

      // Scope to the page-content container (.min-w-0, NavShell's content
      // wrapper) rather than the bare `button` selector. A bare selector also
      // catches the mobile "Open menu" <button>, which is rendered in the DOM
      // at desktop widths (md:hidden => display:none => 0x0) and would be a
      // false-positive tap-target failure unrelated to the Button component.
      await expectTapTargets(
        authenticatedPage,
        '.min-w-0 button',
        `members buttons @ ${width}px`,
      );
    });
  }
});
