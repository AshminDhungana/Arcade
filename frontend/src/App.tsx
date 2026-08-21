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

// Mobile routes (lazy-loaded)
const MobileLayout = lazy(() => import('./components/mobile/MobileLayout').then(m => ({ default: m.MobileLayout })));
const MobileDashboard = lazy(() => import('./pages/mobile/MobileDashboard').then(m => ({ default: m.MobileDashboard })));
const MobileSessions = lazy(() => import('./pages/mobile/MobileSessions').then(m => ({ default: m.MobileSessions })));
const MobileShifts = lazy(() => import('./pages/mobile/MobileShifts').then(m => ({ default: m.MobileShifts })));
const MobileSettings = lazy(() => import('./pages/mobile/MobileSettings').then(m => ({ default: m.MobileSettings })));

// Mobile loading fallback
function MobileLoadingFallback() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center" data-testid="mobile-loading">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  );
}

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

        {/* Mobile routes */}
        <Route
          path="/mobile"
          element={
            <ProtectedRoute>
              <Suspense fallback={<MobileLoadingFallback />}>
                <MobileLayout />
              </Suspense>
            </ProtectedRoute>
          }
        >
          <Route index element={<MobileDashboard />} />
          <Route path="sessions" element={<MobileSessions />} />
          <Route path="shifts" element={<MobileShifts />} />
          <Route path="settings" element={<MobileSettings />} />
        </Route>
      </Routes>
      <ToastViewport />
    </>
  );
}
