import { test, expect, VIEWPORTS } from './fixtures';
import { expectNoHorizontalOverflow, expectTapTargets } from './support/assertions';

const ROUTES = ['/', '/members', '/analytics', '/events', '/settings'] as const;
const NAV_LABEL: Record<string, string> = {
  '/': 'Dashboard',
  '/members': 'Members',
  '/analytics': 'Analytics',
  '/events': 'Events',
  '/settings': 'Settings',
};
const HEADING: Record<string, RegExp> = {
  '/': /arcade dashboard/i,
  '/members': /members/i,
  '/analytics': /analytics/i,
  '/events': /events/i,
  '/settings': /settings/i,
};

/** Client-side SPA navigation (no full reload — auth store is in-memory). */
async function navToRoute(page: import('@playwright/test').Page, route: string): Promise<void> {
  const width = page.viewportSize()?.width ?? 375;
  if (width < 768) {
    await page.getByRole('button', { name: /open menu/i }).click();
  }
  await page.getByRole('link', { name: NAV_LABEL[route], exact: true }).first().click();
  await expect(page).toHaveURL(route);
  await expect(page.getByRole('heading', { name: HEADING[route] })).toBeVisible();
}

test.describe('Responsive matrix (AC-05)', () => {
  for (const route of ROUTES) {
    for (const width of VIEWPORTS) {
      test(`no overflow on ${route} @ ${width}px`, async ({ authenticatedPage }) => {
        await authenticatedPage.setViewportSize({ width, height: 800 });
        await navToRoute(authenticatedPage, route);
        await expectNoHorizontalOverflow(authenticatedPage, `${route} @ ${width}px`);
      });
    }
  }

  // Tap-target sweep on the dashboard (most-used owner view from their phone)
  for (const width of VIEWPORTS) {
    test(`dashboard tap targets >= 44px @ ${width}px`, async ({ authenticatedPage }) => {
      await authenticatedPage.setViewportSize({ width, height: 800 });
      await navToRoute(authenticatedPage, '/');
      await expectTapTargets(authenticatedPage, 'button', `dashboard buttons @ ${width}px`);
    });
  }
});
