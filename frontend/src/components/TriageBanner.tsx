import { AlertTriangle, ArrowLeft, HelpCircle } from 'lucide-react';
import { alternativeKcal } from '../lib/format';
import type { ApiError } from '../lib/errors';
import { describeApiError } from '../lib/errors';
import type { AlternativeWithNutrition, Triage } from '../lib/types';

interface TriageBannerProps {
  triage: Triage;
  /** Label of the alternative currently being viewed (if any). */
  viewingLabel: string | null;
  /** Label of the alternative being fetched (if any). */
  loadingLabel: string | null;
  error: ApiError | null;
  onSelect: (alt: AlternativeWithNutrition) => void;
  onReset: () => void;
}

export function TriageBanner({
  triage,
  viewingLabel,
  loadingLabel,
  error,
  onSelect,
  onReset,
}: TriageBannerProps) {
  if (triage.level === 'confident') return null;
  const uncertain = triage.level === 'uncertain';
  const Icon = uncertain ? HelpCircle : AlertTriangle;
  const viewing = triage.alternatives_with_nutrition.find((a) => a.label === viewingLabel);

  return (
    <section
      aria-label="Triage"
      data-testid="triage-banner"
      className={`rounded-2xl border-2 border-ink p-4 text-night shadow-brutal sm:p-5 ${
        uncertain ? 'bg-coral' : 'bg-sun'
      }`}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border-2 border-ink bg-cream"
        >
          <Icon size={22} strokeWidth={2.5} />
        </span>
        <div className="min-w-0">
          <h2 className="font-display text-lg font-bold">
            {uncertain ? 'Uncertain prediction' : 'Please double-check'}
          </h2>
          <p className="text-sm font-medium">{triage.message}</p>
        </div>
      </div>

      {triage.alternatives_with_nutrition.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-bold uppercase tracking-wide">
            Tap an alternative to see its nutrition
          </p>
          <ul className="flex flex-wrap gap-2">
            {triage.alternatives_with_nutrition.map((alt) => {
              const active = viewingLabel === alt.label;
              const kcal = alternativeKcal(alt);
              return (
                <li key={alt.label}>
                  <button
                    type="button"
                    aria-pressed={active}
                    disabled={loadingLabel !== null}
                    onClick={() => onSelect(alt)}
                    className={`min-h-[44px] rounded-full border-2 border-ink px-4 py-1.5 text-left text-sm font-bold text-night shadow-brutal-sm transition-all duration-100 hover:translate-x-px hover:translate-y-px motion-reduce:transition-none motion-reduce:hover:translate-x-0 motion-reduce:hover:translate-y-0 disabled:opacity-60 ${
                      active ? 'bg-teal' : 'bg-cream'
                    }`}
                  >
                    {alt.display_name}
                    <span className="tabular ml-2 font-medium">
                      {(alt.confidence * 100).toFixed(0)}%
                      {kcal !== null ? ` \u00b7 ${Math.round(kcal)} kcal` : ''}
                    </span>
                    {loadingLabel === alt.label && <span className="ml-2">&hellip;</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {viewing && (
        <div className="mt-4 flex flex-wrap items-center gap-3 rounded-xl border-2 border-ink bg-cream p-3">
          <span className="tag-pill bg-teal">Viewing alternative</span>
          <span className="font-bold">{viewing.display_name}</span>
          <button type="button" className="btn-brutal ml-auto bg-surface !text-ink" onClick={onReset}>
            <ArrowLeft size={16} strokeWidth={2.5} aria-hidden="true" />
            Back to top prediction
          </button>
        </div>
      )}

      {error && (
        <p role="alert" className="mt-3 rounded-xl border-2 border-ink bg-cream px-3 py-2 text-sm font-bold">
          {describeApiError(error).title}: {describeApiError(error).message}
        </p>
      )}
    </section>
  );
}
