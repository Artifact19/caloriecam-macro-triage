import { Moon, Sun } from 'lucide-react';
import type { BackendStatus } from '../hooks/useHealth';

interface HeaderProps {
  dark: boolean;
  onToggleDark: () => void;
  backendStatus: BackendStatus;
}

const STATUS_TAG: Record<BackendStatus, { label: string; className: string }> = {
  checking: { label: 'Checking scanner\u2026', className: 'bg-sun' },
  ok: { label: 'Ready to Scan', className: 'bg-teal' },
  no_model: { label: 'Scanner warming up', className: 'bg-tangerine' },
  unreachable: { label: 'Scanner offline', className: 'bg-coral' },
};

export function Header({ dark, onToggleDark, backendStatus }: HeaderProps) {
  const tag = STATUS_TAG[backendStatus];
  return (
    <header className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-4 pt-5 sm:px-6">
      <div className="flex items-center gap-3.5">
        <img
          src="/app-icon.jpg"
          alt="CalorieCAM mascot"
          className="h-12 w-12 shrink-0 rounded-2xl border-2 border-ink object-cover shadow-brutal"
        />
        <div className="min-w-0">
          <h1 className="font-display text-2xl font-bold leading-none sm:text-3xl">CalorieCAM</h1>
          <p className="mt-1 text-xs font-medium text-muted sm:text-sm">
            Smart visual meal recognition &amp; instant nutrition tracker.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <span className={`tag-pill ${tag.className}`} role="status" data-testid="backend-status">
          <span
            aria-hidden="true"
            className="inline-block h-2.5 w-2.5 rounded-full border-2 border-night bg-cream"
          />
          {tag.label}
        </span>
        <button
          type="button"
          role="switch"
          aria-checked={dark}
          aria-label="Dark mode"
          onClick={onToggleDark}
          className="relative flex h-11 w-[76px] shrink-0 items-center rounded-full border-2 border-ink bg-surface shadow-brutal-sm transition-colors"
        >
          <span
            aria-hidden="true"
            className={`absolute top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border-2 border-ink text-night transition-all duration-150 motion-reduce:transition-none ${
              dark ? 'left-[38px] bg-grape' : 'left-1 bg-sun'
            }`}
          >
            {dark ? <Moon size={16} strokeWidth={2.5} /> : <Sun size={16} strokeWidth={2.5} />}
          </span>
        </button>
      </div>
    </header>
  );
}
