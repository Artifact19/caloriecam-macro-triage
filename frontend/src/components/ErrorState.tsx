import { AlertOctagon, RotateCcw, X } from 'lucide-react';
import { describeApiError } from '../lib/errors';
import type { ApiError } from '../lib/errors';

interface ErrorStateProps {
  error: ApiError;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function ErrorState({ error, onRetry, onDismiss }: ErrorStateProps) {
  const copy = describeApiError(error);
  return (
    <div role="alert" className="brutal-card overflow-hidden" data-testid="error-state">
      <div className="flex items-start gap-3 border-b-2 border-ink bg-coral p-4 text-night">
        <span
          aria-hidden="true"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border-2 border-ink bg-cream"
        >
          <AlertOctagon size={24} strokeWidth={2.5} />
        </span>
        <div className="min-w-0">
          <h2 className="font-display text-xl font-bold">{copy.title}</h2>
          {error.status !== undefined && (
            <span className="tag-pill mt-1 bg-cream">HTTP {error.status}</span>
          )}
        </div>
      </div>
      <div className="space-y-4 p-4">
        <p className="text-sm font-medium">{copy.message}</p>
        <div className="flex flex-wrap gap-3">
          {onRetry && (
            <button type="button" className="btn-brutal bg-teal" onClick={onRetry}>
              <RotateCcw size={18} strokeWidth={2.5} aria-hidden="true" />
              {copy.retryable ? 'Try again' : 'Re-analyze'}
            </button>
          )}
          {onDismiss && (
            <button type="button" className="btn-brutal bg-surface !text-ink" onClick={onDismiss}>
              <X size={18} strokeWidth={2.5} aria-hidden="true" />
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
