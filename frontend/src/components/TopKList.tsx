import { motion, useReducedMotion } from 'framer-motion';
import type { Prediction } from '../lib/types';

interface TopKListProps {
  items: Prediction[];
  /** Label currently shown in the nutrition card (highlighted). */
  activeLabel?: string;
}

const BAR_COLORS = ['bg-coral', 'bg-grape', 'bg-teal'];

export function TopKList({ items, activeLabel }: TopKListProps) {
  const reduceMotion = useReducedMotion();
  const top = items.slice(0, 3);
  return (
    <div className="brutal-card p-4 sm:p-5">
      <h2 className="mb-3 font-display text-lg font-bold">Top 3 predictions</h2>
      <ol className="space-y-3">
        {top.map((item, i) => {
          const pct = Math.min(100, Math.max(0, item.confidence * 100));
          const active = activeLabel === item.label;
          return (
            <li key={item.label} aria-current={active ? 'true' : undefined}>
              <div className="mb-1 flex items-baseline justify-between gap-2">
                <span className="flex min-w-0 items-center gap-2 font-bold">
                  <span
                    aria-hidden="true"
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border-2 border-ink bg-sun text-xs text-night"
                  >
                    {i + 1}
                  </span>
                  <span className="truncate">{item.display_name}</span>
                </span>
                <span className="tabular shrink-0 font-display font-bold">{pct.toFixed(1)}%</span>
              </div>
              <div
                className="progress-track"
                role="progressbar"
                aria-label={`${item.display_name} confidence`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(pct)}
              >
                <motion.div
                  className={`h-full border-r-2 border-ink ${BAR_COLORS[i % BAR_COLORS.length]}`}
                  initial={{ width: reduceMotion ? `${pct}%` : 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: reduceMotion ? 0 : 0.7, ease: 'easeOut', delay: i * 0.08 }}
                />
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
