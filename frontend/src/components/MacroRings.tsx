import { PolarAngleAxis, RadialBar, RadialBarChart } from 'recharts';
import { useReducedMotion } from 'framer-motion';
import { formatGrams } from '../lib/format';
import type { MacroEnergySplit } from '../lib/types';

interface MacroRingsProps {
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  split: MacroEnergySplit;
}

export const MACRO_COLORS = {
  protein: '#A78BFA',
  carbs: '#FFE066',
  fat: '#F25F5C',
} as const;

interface RingDef {
  key: 'protein' | 'carbs' | 'fat';
  name: string;
  grams: number;
  pct: number;
  color: string;
}

/** Three progress rings (Recharts RadialBarChart) + a stacked energy-split bar. */
export function MacroRings({ protein_g, carbs_g, fat_g, split }: MacroRingsProps) {
  const reduceMotion = useReducedMotion();
  const rings: RingDef[] = [
    { key: 'protein', name: 'Protein', grams: protein_g, pct: split.protein_pct, color: MACRO_COLORS.protein },
    { key: 'carbs', name: 'Carbs', grams: carbs_g, pct: split.carbs_pct, color: MACRO_COLORS.carbs },
    { key: 'fat', name: 'Fat', grams: fat_g, pct: split.fat_pct, color: MACRO_COLORS.fat },
  ];

  return (
    <div className="space-y-4">
      <ul className="grid grid-cols-3 gap-2" aria-label="Macro breakdown">
        {rings.map((r) => (
          <li key={r.key} className="flex flex-col items-center text-center">
            <div className="relative h-[104px] w-[104px]" data-testid={`ring-${r.key}`}>
              <RadialBarChart
                width={104}
                height={104}
                innerRadius="68%"
                outerRadius="100%"
                data={[{ name: r.name, value: Math.max(0, Math.min(100, r.pct)), fill: r.color }]}
                startAngle={90}
                endAngle={-270}
                barSize={14}
              >
                <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                <RadialBar
                  dataKey="value"
                  background={{ fill: 'var(--c-sunken)' }}
                  cornerRadius={0}
                  stroke="#141414"
                  strokeWidth={2}
                  isAnimationActive={!reduceMotion}
                />
              </RadialBarChart>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center leading-tight">
                <span className="tabular font-display text-lg font-bold">{formatGrams(r.grams)}</span>
              </div>
            </div>
            <span className="mt-1 text-sm font-bold">{r.name}</span>
            <span className="tabular text-xs font-medium text-muted">
              {r.pct.toFixed(0)}% of macro kcal
            </span>
          </li>
        ))}
      </ul>

      <div>
        <div
          role="img"
          aria-label={`Macro energy split: protein ${split.protein_pct.toFixed(0)} percent, carbs ${split.carbs_pct.toFixed(0)} percent, fat ${split.fat_pct.toFixed(0)} percent`}
          className="flex h-8 w-full overflow-hidden rounded-full border-2 border-ink bg-surface"
        >
          {rings.map((r, i) => (
            <div
              key={r.key}
              className={`flex items-center justify-center text-[11px] font-bold text-night ${
                i < rings.length - 1 ? 'border-r-2 border-ink' : ''
              }`}
              style={{ width: `${Math.max(0, r.pct)}%`, backgroundColor: r.color }}
            >
              {r.pct >= 12 ? `${r.name[0]} ${r.pct.toFixed(0)}%` : ''}
            </div>
          ))}
        </div>
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs font-bold" aria-hidden="true">
          {rings.map((r) => (
            <li key={r.key} className="flex items-center gap-1.5">
              <span
                className="inline-block h-3 w-3 rounded-sm border-2 border-ink"
                style={{ backgroundColor: r.color }}
              />
              {r.name}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
