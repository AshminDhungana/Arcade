import { useToastStore } from '@/store/toastStore';
import { CheckCircle, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';

interface ToastItemProps {
  toast: {
    id: string;
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    persistent?: boolean;
    onClick?: () => void;
    dismissLabel?: string;
  };
}

function ToastItem({ toast }: ToastItemProps) {
  const dismiss = useToastStore((state) => state.dismiss);

  const handleClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('[data-dismiss]')) return;
    if (toast.onClick) {
      toast.onClick();
    } else {
      // Backward compat: dismiss on click if no onClick handler
      dismiss(toast.id);
    }
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    dismiss(toast.id);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      dismiss(toast.id);
    }
  };

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-success" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-destructive" />;
      case 'info':
        return <Info className="h-4 w-4 text-primary" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-warning" />;
    }
  };

  return (
    <div
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role="alert"
      tabIndex={0}
      className={`flex cursor-pointer items-center gap-2 rounded-lg px-4 py-3 text-sm shadow-xl bg-popover text-foreground border-border backdrop-blur-sm ${
        toast.persistent ? 'animate-none' : 'animate-in slide-in-from-right-full duration-300'
      }`}
      data-testid="toast"
    >
      {getIcon()}
      <span className="font-medium flex-1">{toast.message}</span>
      {toast.dismissLabel && (
        <button
          className="toast-dismiss flex items-center justify-center p-1 rounded hover:bg-accent transition-colors"
          onClick={handleDismiss}
          aria-label={toast.dismissLabel}
          data-dismiss
          data-testid="toast-dismiss"
        >
          <X size={14} strokeWidth={2.5} />
        </button>
      )}
    </div>
  );
}

export function ToastViewport() {
  const { toasts } = useToastStore();

  return (
    <div role="status" aria-live="polite" className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} />
      ))}
    </div>
  );
}