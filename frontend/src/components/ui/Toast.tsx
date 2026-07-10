import { useToastStore } from '@/store/toastStore';
import { CheckCircle, AlertCircle } from 'lucide-react';

export function ToastViewport() {
  const { toasts, remove } = useToastStore();

  return (
    <div role="status" aria-live="polite" className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          onClick={() => remove(t.id)}
          className={`flex cursor-pointer items-center gap-2 rounded-lg px-4 py-3 text-sm shadow-xl backdrop-blur-sm ${
            t.type === 'success'
              ? 'border border-emerald-500/20 bg-emerald-900/90 text-emerald-200'
              : 'border border-red-800/50 bg-red-900/90 text-red-200'
          }`}
        >
          {t.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
          {t.message}
        </div>
      ))}
    </div>
  );
}
