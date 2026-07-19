import { AlertCircle } from 'lucide-react';
import { Alert } from './Alert';
import { Button } from './Button';

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Alert variant="destructive" className="flex items-center justify-between gap-4">
      <div className="flex items-center gap-2">
        <AlertCircle className="h-4 w-4" data-testid="alert-circle" />
        <span>{message}</span>
      </div>
      {onRetry && (
        <Button variant="danger" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </Alert>
  );
}
