import { useState } from 'react';
import { Flame, Leaf } from 'lucide-react';
import { CountUp } from './CountUp';
import { MacroRings } from './MacroRings';
import { PortionControl } from './PortionControl';
import { computeEnergySplit, formatGrams, scaleNutrition } from '../lib/format';
import type { Nutrition } from '../lib/types';

interface NutritionCardProps {
  nutrition: Nutrition;
  /** Shows a "Viewing alternative" tag when the card shows a non-top-1 dish. */
  viewingAlternative?: boolean;
}

/**
 * Calories + macros, scaled locally by the selected portion (no extra API calls).
 * Remount (via `key`) when the dish changes to reset the portion to the server's servings.
 */
export function NutritionCard({ nutrition, viewingAlternative = false }: NutritionCardProps) {
  const [servings, setServings] = useState(nutrition.servings > 0 ? nutrition.servings : 1);
  const scaled = scaleNutrition(nutrition, servings);
  const split = nutrition.macro_energy_split ?? computeEnergySplit(nutrition);

  return (
    <div className="brutal-card overflow-hidden" data-testid="nutrition-card">
      <div className="border-b-2 border-ink bg-panel p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="font-display text-lg font-bold">{nutrition.display_name}</h2>
          {viewingAlternative && <span className="tag-pill bg-teal">Viewing alternative</span>}
        </div>
        <div className="mt-2 flex items-end gap-2">
          <Flame size={28} strokeWidth={2.5} className="mb-1 shrink-0 text-coral" aria-hidden="true" />
          <CountUp
            value={scaled.calories_kcal}
            className="font-display text-5xl font-bold leading-none sm:text-6xl"
            testId="calories-total"
          />
          <span className="mb-1 font-display text-lg font-bold">kcal</span>
        </div>
        <p className="mt-2 text-sm font-medium text-muted" data-testid="serving-description">
          {servings}&times; &middot; {nutrition.serving_description}
        </p>
      </div>

      <div className="space-y-5 p-4 sm:p-5">
        <MacroRings
          protein_g={scaled.protein_g}
          carbs_g={scaled.carbs_g}
          fat_g={scaled.fat_g}
          split={split}
        />

        <div className="flex flex-wrap items-center gap-2">
          <span className="tag-pill bg-teal">
            <Leaf size={14} strokeWidth={2.5} aria-hidden="true" />
            Fiber <span data-testid="fiber-value">{formatGrams(scaled.fiber_g)}</span>
          </span>
        </div>

        <PortionControl value={servings} onChange={setServings} />

        <p className="border-t-2 border-dashed border-ink pt-3 text-xs font-medium text-muted">
          Estimates are approximate and not medical advice.
        </p>
      </div>
    </div>
  );
}
