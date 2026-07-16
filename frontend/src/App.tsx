import { Routes, Route } from 'react-router-dom';
import Login from './pages/Login';
import DashboardPage from './pages/Dashboard';
import { MembersPage } from './pages/Members';
import { AnalyticsPage } from './pages/Analytics';
import { EventsPage } from './pages/Events';
import SettingsPage from './pages/Settings';
import ProtectedRoute from './components/ProtectedRoute';
import RequireFeature from './components/RequireFeature';
import { useFeatureFlags } from './api/featureFlags';
import { ToastViewport } from '@/components/ui/Toast';
import { NavShell } from './components/NavShell';

export default function App() {
  // Bootstrap feature flags from GET /api/settings on mount
  useFeatureFlags();

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
                  <MembersPage />
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
                <AnalyticsPage />
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
                  <EventsPage />
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
                <SettingsPage />
              </NavShell>
            </ProtectedRoute>
          }
        />
      </Routes>
      <ToastViewport />
    </>
  );
}
