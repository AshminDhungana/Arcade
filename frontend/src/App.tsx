import { useWebSocket } from '@/hooks/useWebSocket';

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

function App() {
  const { status } = useWebSocket();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-slate-900 p-4">
      <h1 className="text-4xl font-bold text-white">Arcade Dashboard</h1>
      <ConnectionBadge status={status} />
      <p className="text-center text-sm text-slate-400">
        Seat grid and session controls will appear here in Feature 2.3.2.
      </p>
    </div>
  );
}

export default App;
