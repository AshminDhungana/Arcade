import { AlertCircle } from 'lucide-react';

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-red-800/50 bg-red-900/10 px-4 py-3 text-sm text-red-300">
      <AlertCircle className="h-4 w-4" data-testid="alert-circle" />
      {message}
      {onRetry && (
        <button onClick={onRetry} className="ml-auto text-red-200 underline">
          Retry
        </button>
      )}
    </div>
  );
}
