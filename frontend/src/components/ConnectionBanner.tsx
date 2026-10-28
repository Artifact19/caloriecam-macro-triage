import { PlugZap, RefreshCw, TerminalSquare } from 'lucide-react';
import type { BackendStatus } from '../hooks/useHealth';
import type { Health } from '../lib/types';

interface ConnectionBannerProps {
  status: BackendStatus;
  health: Health | null;
  onRetry: () => void;
}

function Code({ children }: { children: string }) {
  return (
    <code className="rounded-md border-2 border-ink bg-cream px-2 py-0.5 font-mono text-sm font-bold text-night">
      {children}
    </code>
  );
}

/** Full-width banner shown when the backend is unreachable or has no model artifacts. */
export function ConnectionBanner({ status, health, onRetry }: ConnectionBannerProps) {
  if (status === 'ok' || status === 'checking') return null;
  const unreachable = status === 'unreachable';
  const missing = health?.missing_artifacts ?? [];

  return (
    <div className="mx-auto mt-5 w-full max-w-6xl px-4 sm:px-6">
      <div
        role="alert"
        data-testid="connection-banner"
        className={`rounded-2xl border-2 border-ink p-4 text-night shadow-brutal sm:p-5 ${
          unreachable ? 'bg-coral' : 'bg-sun'
        }`}
      >
        <div className="flex flex-wrap items-start gap-3">
          <span
            aria-hidden="true"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border-2 border-ink bg-cream"
          >
            {unreachable ? <PlugZap size={22} strokeWidth={2.5} /> : <TerminalSquare size={22} strokeWidth={2.5} />}
          </span>
          <div className="min-w-0 flex-1 space-y-2">
            <h2 className="font-display text-lg font-bold">
              {unreachable ? 'Backend is not running' : 'Model artifacts are missing'}
            </h2>
            {unreachable ? (
              <p className="text-sm font-medium">
                Start the backend with <Code>run_backend.bat</Code> (Windows) or{' '}
                <Code>./run_backend.sh</Code> (Linux/macOS). This page keeps checking automatically.
              </p>
            ) : (
              <>
                <p className="text-sm font-medium">
                  The backend is running but no model is loaded. Run the notebooks to train and export
                  it: <Code>python scripts/run_notebooks.py</Code>, then restart the backend.
                </p>
                {missing.length > 0 && (
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wide">Missing artifacts</p>
                    <ul className="mt-1 flex flex-wrap gap-2">
                      {missing.map((m) => (
                        <li key={m}>
                          <Code>{m}</Code>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
          <button type="button" className="btn-brutal bg-cream" onClick={onRetry}>
            <RefreshCw size={18} strokeWidth={2.5} aria-hidden="true" />
            Check again
          </button>
        </div>
      </div>
    </div>
  );
}
