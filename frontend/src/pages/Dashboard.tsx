import { useWebSocket } from '@/hooks/useWebSocket';
import { SeatGrid } from '@/components/SeatGrid';

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

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">Arcade Dashboard</h1>
          <ConnectionBadge status={status} />
        </div>
      </header>

      {/* Main content */}
      <main className="p-6">
        <SeatGrid />
      </main>
    </div>
  );
}
