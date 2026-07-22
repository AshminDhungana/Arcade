import { useWebSocket } from '@/hooks/useWebSocket';
import { SeatGrid } from '@/components/SeatGrid';
import { UnprintedInvoices } from '@/components/UnprintedInvoices';
import { useAuthStore } from '@/store/authStore';
import { bulkForceOverlay } from '@/api/seats';
import { toast } from '@/store/toastStore';
import { Lock } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/Button';

function ConnectionBadge({
  status,
}: {
  status: 'connecting' | 'connected' | 'disconnected';
}) {
  const styles = {
    connected: 'bg-success/15 text-success',
    connecting: 'bg-warning/15 text-warning',
    disconnected: 'bg-destructive/15 text-destructive',
  };

  const labels = {
    connected: '',
    connecting: 'Connecting…',
    disconnected: 'Connection lost',
  };

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${styles[status]}`}
      aria-label="Connection status"
    >
      <span
        className={`h-2 w-2 rounded-full bg-current ${status === 'connecting' ? 'animate-pulse' : ''}`}
      />
      {labels[status] && <span>{labels[status]}</span>}
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
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-20 border-b border-border bg-card/95 px-6 py-4 backdrop-blur-sm">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-xl font-bold text-foreground">Arcade Dashboard</h1>
          <div className="flex items-center gap-3">
            {isAdmin && (
              <Button
                variant="secondary"
                onClick={handleLockIdle}
                disabled={isLocking}
                loading={isLocking}
                aria-label="Lock all idle seats"
              >
                <Lock className="size-4" aria-hidden="true" />
                <span>Lock all idle seats</span>
              </Button>
            )}
            <ConnectionBadge status={status} />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl space-y-6 p-6">
        <UnprintedInvoices />
        <SeatGrid />
      </main>
    </div>
  );
}
