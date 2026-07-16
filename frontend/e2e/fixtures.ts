import { test as base, expect, type Page } from '@playwright/test';

/**
 * All feature flags ON so every route is reachable in tests.
 *
 * IMPORTANT: values are STRINGS, not booleans. The app parses flags with
 * `value?.toLowerCase() === 'true'` (see src/api/featureFlags.ts:41), so a JSON
 * boolean would short-circuit to `undefined` and every flag would resolve to
 * `false`, hiding feature-gated routes (Members/Events, etc.).
 */
const FLAGS = {
  enable_members: 'true',
  enable_packages: 'true',
  enable_pos: 'true',
  enable_inventory: 'true',
  enable_reservations: 'true',
  enable_vouchers: 'true',
  enable_tournaments: 'true',
  enable_expense_tracking: 'true',
  enable_health_monitoring: 'true',
  require_member_for_session: 'false',
} as const;

/** Seats incl. one IN_USE seat with a session (drives the SessionDrawer test). */
const SEATS = [
  { id: 's1', name: 'PC-01', status: 'AVAILABLE', is_console: false, zone_id: 'z1', notes: '' },
  { id: 's2', name: 'PC-02', status: 'PAUSED', is_console: false, zone_id: 'z1', notes: '' },
  {
    id: 's3',
    name: 'PC-03',
    status: 'IN_USE',
    is_console: false,
    zone_id: 'z1',
    current_session_id: 'sess-1',
    notes: '',
  },
];

/**
 * Intercept backend API calls and abort the WebSocket.
 *
 * IMPORTANT: the route glob is the catch-all pattern (not the "/api/" one). The
 * app eagerly imports source modules such as /src/api/featureFlags.ts; an "/api/"
 * glob would also match those and fulfill them as JSON, breaking the Vite module
 * graph and crashing the app before render. We therefore intercept ONLY top-level
 * /api/... paths (the real backend API) and route.fallback() everything else
 * (including /src/...), so Vite can serve it.
 */
export async function mockApi(page: Page): Promise<void> {
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path.startsWith('/ws/')) return route.abort();
    if (!path.startsWith('/api/')) return route.fallback();
    const method = route.request().method();
    if (url.pathname === '/api/auth/login' && method === 'POST') {
      return route.fulfill({
        json: {
          access_token: 'test-token',
          token_type: 'bearer',
          expires_in: 3600,
          staff: { id: 's1', name: 'Owner', role: 'admin', is_active: true },
        },
      });
    }
    if (url.pathname === '/api/settings') return route.fulfill({ json: FLAGS });
    if (url.pathname === '/api/seats') return route.fulfill({ json: SEATS });
    if (url.pathname === '/api/members')
      return route.fulfill({
        json: [
          { id: 'm1', name: 'Alice', phone: '9800000001', wallet_balance_paise: 5000, tier: 'SILVER' },
        ],
      });
    if (url.pathname === '/api/analytics/summary')
      return route.fulfill({
        json: {
          weekly_revenue: [],
          zone_utilisation: [],
          top_pos_items: [],
          member_registration_trend: [],
          health_alerts: [],
        },
      });
    if (url.pathname === '/api/events') return route.fulfill({ json: [] });
    if (url.pathname.startsWith('/api/events/summary')) return route.fulfill({ json: { total_events: 0 } });
    if (url.pathname === '/api/menu') return route.fulfill({ json: [] });
    return route.fulfill({ json: {} });
  });
}

/** Log in through the real UI (auth store is in-memory, so we drive the form). */
export async function login(page: Page): Promise<void> {
  await page.goto('/login');
  await page.fill('#staffId', 'STAFF-001');
  await page.fill('#pin', '1234');
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page.getByRole('heading', { name: /arcade dashboard/i })).toBeVisible();
}

export const VIEWPORTS = [375, 390, 412, 768] as const;

export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    await mockApi(page);
    await login(page);
    await use(page);
  },
});

export { expect };
