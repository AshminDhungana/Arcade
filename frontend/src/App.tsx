import { Routes, Route } from 'react-router-dom';
import Login from './pages/Login';
import DashboardPage from './pages/Dashboard';
import ProtectedRoute from './components/ProtectedRoute';
import { useFeatureFlags } from './api/featureFlags';
import { ToastViewport } from '@/components/ui/Toast';

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
              <DashboardPage />
            </ProtectedRoute>
          }
        />
      </Routes>
      <ToastViewport />
    </>
  );
}
