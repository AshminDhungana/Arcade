import type { Seat } from '@/types/seat';
import { Pause, Play, Power, Settings, ShoppingCart, Heart } from 'lucide-react';

interface SeatActionModalProps {
  seat: Seat;
  onClose: () => void;
}

/** Modal displayed when a seat card is clicked.
 *  Displays seat details and a list of available actions.
 *  Actions are placeholders — wiring to API calls comes in later features. */
export function SeatActionModal({ seat, onClose }: SeatActionModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="seat-modal-title"
    >
      <div className="w-full max-w-md rounded-lg bg-slate-800 p-6 shadow-xl border border-slate-700">
        <header className="mb-4 flex items-center justify-between">
          <h2 id="seat-modal-title" className="text-xl font-bold text-white">
            {seat.name}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1"
            aria-label="Close modal"
          >
            ×
          </button>
        </header>

        <section className="mb-4 space-y-2 text-sm text-slate-300">
          <p>Status: <span className="text-white font-medium">{seat.status.replace('_', ' ')}</span></p>
          <p>Zone: <span className="text-white">{seat.zone_id}</span></p>
          {seat.notes && <p>Note: {seat.notes}</p>}
        </section>

        <nav aria-label="Seat actions" className="grid grid-cols-2 gap-2">
          {seat.status === 'AVAILABLE' && (
            <ActionButton icon={<Play className="h-5 w-5" />} label="Start Session" variant="primary" />
          )}
          {seat.status === 'IN_USE' && (
            <ActionButton icon={<Pause className="h-5 w-5" />} label="Pause Session" variant="secondary" />
          )}
          {seat.status === 'PAUSED' && (
            <ActionButton icon={<Play className="h-5 w-5" />} label="Resume Session" variant="secondary" />
          )}
          <ActionButton icon={<ShoppingCart className="h-5 w-5" />} label="Checkout" variant="emerald" />
          <ActionButton icon={<Power className="h-5 w-5" />} label="Wake-on-LAN" variant="secondary" />
          <ActionButton icon={<Heart className="h-5 w-5" />} label="View Health" variant="secondary" />
          <ActionButton icon={<Settings className="h-5 w-5" />} label="Maintenance" variant="secondary" />
        </nav>
      </div>
    </div>
  );
}

interface ActionButtonProps {
  icon: React.ReactNode;
  label: string;
  variant: 'primary' | 'secondary' | 'emerald';
  onClick?: () => void;
}

function ActionButton({ icon, label, variant, onClick }: ActionButtonProps) {
  const base = 'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-800';
  const styles = {
    primary: 'bg-blue-600 text-white hover:bg-blue-500 focus:ring-blue-500',
    secondary: 'bg-slate-700 text-slate-200 hover:bg-slate-600 focus:ring-slate-400',
    emerald: 'bg-emerald-600 text-white hover:bg-emerald-500 focus:ring-emerald-500',
  };

  return (
    <button type="button" onClick={onClick} className={`${base} ${styles[variant]}`}>
      {icon}
      <span>{label}</span>
    </button>
  );
}
