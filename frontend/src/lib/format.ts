import type { MacroEnergySplit, MacroFields, Nutrition, AlternativeWithNutrition } from './types';

export function formatMs(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A';
  return `${value.toFixed(1)} ms`;
}

export function formatPct(fraction: number, digits = 0): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

export function formatGrams(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1)} g`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatServings(servings: number): string {
  return `${Number.isInteger(servings) ? servings.toFixed(0) : String(servings)}\u00d7`;
}

const ENGINE_LABELS: Record<string, string> = {
  onnx_int8_static: 'INT8 \u00b7 static',
  onnx_int8_dynamic: 'INT8 \u00b7 dynamic',
  onnx_fp32: 'FP32 \u00b7 ONNX',
  pytorch: 'FP32 \u00b7 PyTorch',
};

export function formatEngine(engine: string): string {
  return ENGINE_LABELS[engine] ?? engine;
}

/** Scale all numeric nutrition fields linearly to a target number of servings. */
export function scaleNutrition(base: Nutrition, targetServings: number): Nutrition {
  const baseServings = base.servings > 0 ? base.servings : 1;
  const factor = targetServings / baseServings;
  return {
    ...base,
    servings: targetServings,
    calories_kcal: base.calories_kcal * factor,
    protein_g: base.protein_g * factor,
    carbs_g: base.carbs_g * factor,
    fat_g: base.fat_g * factor,
    fiber_g: base.fiber_g * factor,
  };
}

/** Percentage of calories from protein/carbs/fat (4/4/9 kcal per gram), normalized to 100. */
export function computeEnergySplit(n: Pick<MacroFields, 'protein_g' | 'carbs_g' | 'fat_g'>): MacroEnergySplit {
  const p = n.protein_g * 4;
  const c = n.carbs_g * 4;
  const f = n.fat_g * 9;
  const total = p + c + f;
  if (total <= 0) return { protein_pct: 0, carbs_pct: 0, fat_pct: 0 };
  return {
    protein_pct: (p / total) * 100,
    carbs_pct: (c / total) * 100,
    fat_pct: (f / total) * 100,
  };
}

const MACRO_KEYS: (keyof MacroFields)[] = [
  'calories_kcal',
  'protein_g',
  'carbs_g',
  'fat_g',
  'fiber_g',
];

/** Build a Nutrition object from a triage alternative if it carries enough data. */
export function nutritionFromAlternative(alt: AlternativeWithNutrition): Nutrition | null {
  if (alt.nutrition) return alt.nutrition;
  if (!MACRO_KEYS.every((k) => typeof alt[k] === 'number')) return null;
  const macros = {
    calories_kcal: alt.calories_kcal as number,
    protein_g: alt.protein_g as number,
    carbs_g: alt.carbs_g as number,
    fat_g: alt.fat_g as number,
    fiber_g: alt.fiber_g as number,
  };
  return {
    dish: alt.label,
    display_name: alt.display_name,
    serving_description: 'standard serving',
    servings: 1,
    ...macros,
    macro_energy_split: computeEnergySplit(macros),
    source: 'triage_alternative',
  };
}

/** kcal for an alternative, if known. */
export function alternativeKcal(alt: AlternativeWithNutrition): number | null {
  if (alt.nutrition) return alt.nutrition.calories_kcal;
  return typeof alt.calories_kcal === 'number' ? alt.calories_kcal : null;
}
