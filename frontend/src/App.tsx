import { useEffect, Suspense, lazy } from 'react';
import { Routes, Route } from 'react-router-dom';
import Login from './pages/Login';
import DashboardPage from './pages/Dashboard';
import ProtectedRoute from './components/ProtectedRoute';
import RequireFeature from './components/RequireFeature';
import { useFeatureFlags } from './api/featureFlags';
import { ToastViewport } from '@/components/ui/Toast';
import { NavShell } from './components/NavShell';
import { useThemeStore } from '@/store/themeStore';
import { PageLoader } from '@/components/ui/PageLoader';

const MembersPage = lazy(() => import('./pages/Members'));
const AnalyticsPage = lazy(() => import('./pages/Analytics'));
const EventsPage = lazy(() => import('./pages/Events'));
const SettingsPage = lazy(() => import('./pages/Settings'));

export default function App() {
  // Bootstrap feature flags from GET /api/settings on mount
  useFeatureFlags();

  // Initialize theme (applies .dark class to <html> if needed)
  const initializeTheme = useThemeStore((s) => s.initialize);
  useEffect(() => {
    initializeTheme();
  }, [initializeTheme]);

  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <NavShell>
                <DashboardPage />
              </NavShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/members"
          element={
            <ProtectedRoute>
              <RequireFeature flag="enable_members">
                <NavShell>
                  <Suspense fallback={<PageLoader />}>
                    <MembersPage />
                  </Suspense>
                </NavShell>
              </RequireFeature>
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <ProtectedRoute>
              <NavShell>
                <Suspense fallback={<PageLoader />}>
                  <AnalyticsPage />
                </Suspense>
              </NavShell>
            </ProtectedRoute>
          }
        />
        <Route
          path="/events"
          element={
            <ProtectedRoute>
              <RequireFeature flag="enable_tournaments">
                <NavShell>
                  <Suspense fallback={<PageLoader />}>
                    <EventsPage />
                  </Suspense>
                </NavShell>
              </RequireFeature>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <NavShell>
                <Suspense fallback={<PageLoader />}>
                  <SettingsPage />
                </Suspense>
              </NavShell>
            </ProtectedRoute>
          }
        />
      </Routes>
      <ToastViewport />
    </>
  );
}
