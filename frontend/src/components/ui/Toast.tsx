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
          className="flex cursor-pointer items-center gap-2 rounded-lg px-4 py-3 text-sm shadow-xl bg-popover text-foreground border-border backdrop-blur-sm"
        >
          {t.type === 'success' ? (
            <CheckCircle className="h-4 w-4 text-success" />
          ) : (
            <AlertCircle className="h-4 w-4 text-destructive" />
          )}
          <span className="font-medium">{t.message}</span>
        </div>
      ))}
    </div>
  );
}
