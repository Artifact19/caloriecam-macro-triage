import { motion, useReducedMotion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { RefreshCw } from 'lucide-react';
import { ConfidenceGauge } from './ConfidenceGauge';
import { HeatmapViewer } from './HeatmapViewer';
import { NutritionCard } from './NutritionCard';
import { TelemetryBadge } from './TelemetryBadge';
import { TopKList } from './TopKList';
import { TriageBanner } from './TriageBanner';
import { formatEngine } from '../lib/format';
import type { PredictState } from '../hooks/usePredict';
import type { AlternativeWithNutrition } from '../lib/types';

interface DashboardProps {
  state: PredictState;
  previewUrl: string;
  onReanalyze: () => void;
  onSelectAlternative: (alt: AlternativeWithNutrition) => void;
  onClearAlternative: () => void;
}

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09 } },
};

const item: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
};

const reducedItem: Variants = {
  hidden: { opacity: 1, y: 0 },
  show: { opacity: 1, y: 0, transition: { duration: 0 } },
};

const LEVEL_TAG = {
  confident: { label: 'Confident', className: 'bg-teal' },
  review: { label: 'Review', className: 'bg-sun' },
  uncertain: { label: 'Uncertain', className: 'bg-coral' },
} as const;

/** Success-state dashboard (staggered entrance). Expects state.result to be non-null. */
export function Dashboard({
  state,
  previewUrl,
  onReanalyze,
  onSelectAlternative,
  onClearAlternative,
}: DashboardProps) {
  const reduceMotion = useReducedMotion();
  const result = state.result;
  if (!result) return null;

  const variants = reduceMotion ? reducedItem : item;
  const view = state.view;
  const nutrition = view ? view.nutrition : result.nutrition;
  const gradcam = view ? view.gradcam : result.gradcam;
  const targetName = view ? view.display_name : result.top1.display_name;
  const tag = LEVEL_TAG[result.triage.level];

  return (
    <motion.div
      className="space-y-5"
      variants={container}
      initial="hidden"
      animate="show"
      data-testid="dashboard"
    >
      <motion.section
        variants={variants}
        aria-label="Top prediction"
        className="brutal-card grid items-center gap-4 p-4 sm:grid-cols-[1fr_auto] sm:p-5"
      >
        <div className="min-w-0 space-y-3">
          <p className="text-xs font-bold uppercase tracking-wide text-muted">Top prediction</p>
          <h2 className="break-words font-display text-4xl font-bold leading-none sm:text-5xl" data-testid="top1-name">
            {result.top1.display_name}
          </h2>
          <div className="flex flex-wrap gap-2">
            <span className={`tag-pill ${tag.className}`}>{tag.label}</span>
            <span className="tag-pill bg-grape">{formatEngine(result.engine)}</span>
          </div>
          <button type="button" className="btn-brutal bg-surface !text-ink" onClick={onReanalyze}>
            <RefreshCw size={18} strokeWidth={2.5} aria-hidden="true" />
            Re-analyze
          </button>
        </div>
        <div className="w-full sm:w-56">
          <ConfidenceGauge confidence={result.top1.confidence} />
        </div>
      </motion.section>

      {result.triage.level !== 'confident' && (
        <motion.div variants={variants}>
          <TriageBanner
            triage={result.triage}
            viewingLabel={view?.label ?? null}
            loadingLabel={state.viewLoading}
            error={state.viewError}
            onSelect={onSelectAlternative}
            onReset={onClearAlternative}
          />
        </motion.div>
      )}

      <motion.div variants={variants}>
        <HeatmapViewer
          originalUrl={previewUrl}
          width={result.image.original_width}
          height={result.image.original_height}
          gradcam={gradcam}
          targetName={targetName}
          busy={state.viewLoading !== null}
        />
      </motion.div>

      <motion.div variants={variants}>
        <NutritionCard
          key={nutrition.dish}
          nutrition={nutrition}
          viewingAlternative={view !== null}
        />
      </motion.div>

      <motion.div variants={variants}>
        <TopKList items={result.topk} activeLabel={view?.label ?? result.top1.label} />
      </motion.div>

      <motion.div variants={variants}>
        <TelemetryBadge
          latency={result.latency}
          engine={result.engine}
          modelVersion={result.model_version}
          roundTripMs={state.roundTripMs}
        />
      </motion.div>
    </motion.div>
  );
}
