import { useState } from 'react';
import { Loader2 } from 'lucide-react';

interface PinConfirmModalProps {
  open: boolean;
  title: string;
  requireReason?: boolean;
  confirmLabel?: string;
  isPending?: boolean;
  onConfirm: (pin: string, reason: string) => void;
  onClose: () => void;
}

export function PinConfirmModal({
  open,
  title,
  requireReason = true,
  confirmLabel = 'Confirm',
  isPending = false,
  onConfirm,
  onClose,
}: PinConfirmModalProps) {
  const [pin, setPin] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const handleSubmit = () => {
    setError(null);
    if (!/^\d{4,}$/.test(pin)) {
      setError('Enter your 4+ digit PIN.');
      return;
    }
    if (requireReason && reason.trim().length === 0) {
      setError('A reason is required.');
      return;
    }
    onConfirm(pin, reason.trim());
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className="w-full max-w-sm rounded-xl border border-slate-700 bg-slate-800 p-5 space-y-4">
        <h3 className="text-base font-bold text-slate-100">{title}</h3>
        <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
          PIN
        </label>
        <input
          type="password"
          inputMode="numeric"
          autoFocus
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100"
          placeholder="••••"
        />
        {requireReason && (
          <>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
              Reason
            </label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100"
              placeholder="Why is this being force-closed?"
            />
          </>
        )}
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-slate-700 py-2 text-slate-300 hover:bg-slate-700 cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isPending}
            className="flex-1 rounded-lg bg-red-600 py-2 font-semibold text-white hover:bg-red-500 disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
          >
            {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
