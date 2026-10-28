/**
 * Types mirroring the backend Pydantic schemas (PROJECT_SPEC.md, Section 6.3).
 * Keep in sync with backend/app/schemas.py.
 */

export type TriageLevel = 'confident' | 'review' | 'uncertain';

export interface Prediction {
  label: string;
  display_name: string;
  confidence: number;
}

export interface MacroEnergySplit {
  protein_pct: number;
  carbs_pct: number;
  fat_pct: number;
}

/** Scalable numeric nutrition fields. */
export interface MacroFields {
  calories_kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
}

export interface Nutrition extends MacroFields {
  dish: string;
  display_name: string;
  serving_description: string;
  servings: number;
  macro_energy_split: MacroEnergySplit;
  source: string;
}

/**
 * Triage alternative (top-3 with kcal and macros). The spec only states "top-3 w/ kcal &
 * macros", so the client accepts either flat macro fields, an embedded `nutrition` object,
 * or just the prediction (in which case nutrition is fetched from /nutrition/{dish}).
 */
export interface AlternativeWithNutrition extends Prediction, Partial<MacroFields> {
  nutrition?: Nutrition;
}

export interface Triage {
  level: TriageLevel;
  message: string;
  alternatives_with_nutrition: AlternativeWithNutrition[];
}

export interface Gradcam {
  target_class: string;
  heatmap_png_base64: string;
  overlay_png_base64: string;
  width: number;
  height: number;
}

export interface Latency {
  preprocess_ms: number;
  inference_ms: number;
  gradcam_ms: number | null;
  postprocess_ms: number;
  total_ms: number;
  classification_path_ms: number;
}

export interface ImageInfo {
  original_width: number;
  original_height: number;
}

export interface PredictResponse {
  top1: Prediction;
  topk: Prediction[];
  triage: Triage;
  nutrition: Nutrition;
  gradcam: Gradcam | null;
  latency: Latency;
  engine: string;
  model_version: string;
  image: ImageInfo;
}

export interface Health {
  status: string;
  model_loaded: boolean;
  engines: string[];
  default_engine: string | null;
  num_classes: number;
  classes: string[];
  model_version: string | null;
  onnxruntime_version: string | null;
  torch_version: string | null;
  uptime_s: number;
  missing_artifacts: string[];
}

export interface PredictOptions {
  top_k?: number;
  gradcam?: boolean;
  engine?: string;
  servings?: number;
  gradcam_class?: string;
}

/** Result of a predict call plus the client-measured round trip. */
export interface PredictResult {
  data: PredictResponse;
  roundTripMs: number;
}
