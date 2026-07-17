import { useWebSocket } from '@/hooks/useWebSocket';
import { SeatGrid } from '@/components/SeatGrid';
import { UnprintedInvoices } from '@/components/UnprintedInvoices';
import { useAuthStore } from '@/store/authStore';
import { bulkForceOverlay } from '@/api/seats';
import { toast } from '@/store/toastStore';
import { Lock } from 'lucide-react';
import { useState } from 'react';

function ConnectionBadge({
  status,
}: {
  status: 'connecting' | 'connected' | 'disconnected';
}) {
  const styles = {
    connected: 'bg-emerald-500',
    connecting: 'bg-amber-500 animate-pulse',
    disconnected: 'bg-red-500',
  };

  const labels = {
    connected: 'Connected',
    connecting: 'Connecting…',
    disconnected: 'Connection lost',
  };

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium text-white ${styles[status]}`}
      aria-label="Connection status"
    >
      <span className="h-2 w-2 rounded-full bg-white" />
      {labels[status]}
    </div>
  );
}

export default function DashboardPage() {
  const { status } = useWebSocket();
  const { staff } = useAuthStore();
  const [isLocking, setIsLocking] = useState(false);

  const isAdmin = staff?.role === 'ADMIN';

  const handleLockIdle = async () => {
    setIsLocking(true);
    try {
      const result = await bulkForceOverlay(true);
      if (result.succeeded.length > 0) {
        toast.success(`Locked ${result.succeeded.length} idle seat(s)`);
      }
      if (result.failed.length > 0) {
        toast.error(`${result.failed.length} seat(s) failed: ${result.failed.map((f) => f.detail).join(', ')}`);
      }
    } catch (err: unknown) {
      toast.error(`Failed to lock idle seats: ${(err as Error).message}`);
    } finally {
      setIsLocking(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">Arcade Dashboard</h1>
          <div className="flex items-center gap-3">
            {isAdmin && (
              <button
                type="button"
                onClick={handleLockIdle}
                disabled={isLocking}
                className="inline-flex items-center gap-2 rounded-lg bg-orange-600 px-4 py-2 text-sm font-medium text-white hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                aria-label="Lock all idle seats"
              >
                <Lock className="h-4 w-4" aria-hidden="true" />
                <span>Lock all idle seats</span>
              </button>
            )}
            <ConnectionBadge status={status} />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="p-6 space-y-6">
        <UnprintedInvoices />
        <SeatGrid />
      </main>
    </div>
  );
}
