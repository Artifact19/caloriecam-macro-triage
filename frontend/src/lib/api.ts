import { ApiError, kindFromStatus, toApiError } from './errors';
import type { Health, Nutrition, PredictOptions, PredictResponse, PredictResult } from './types';

export const API_BASE = '/api';

async function readError(res: Response): Promise<ApiError> {
  let detail: string | undefined;
  let code: string | undefined;
  try {
    const body: unknown = await res.json();
    if (body && typeof body === 'object') {
      const b = body as { detail?: unknown; code?: unknown };
      if (typeof b.detail === 'string') detail = b.detail;
      else if (b.detail !== undefined) detail = JSON.stringify(b.detail);
      if (typeof b.code === 'string') code = b.code;
    }
  } catch {
    /* body was not JSON */
  }
  return new ApiError(kindFromStatus(res.status), detail ?? `Request failed (${res.status}).`, {
    status: res.status,
    detail,
    code,
  });
}

async function request(url: string, init: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    throw toApiError(err);
  }
  if (!res.ok) throw await readError(res);
  return res;
}

function buildQuery(params: Record<string, string | number | boolean | undefined>): string {
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') qs.set(key, String(value));
  }
  const s = qs.toString();
  return s ? `?${s}` : '';
}

/** POST /api/predict. Also measures the client round-trip with performance.now(). */
export async function predict(
  file: File,
  opts: PredictOptions = {},
  signal?: AbortSignal,
): Promise<PredictResult> {
  const form = new FormData();
  form.append('file', file, file.name);
  const query = buildQuery({
    top_k: opts.top_k,
    gradcam: opts.gradcam,
    engine: opts.engine,
    servings: opts.servings,
    gradcam_class: opts.gradcam_class,
  });
  const started = performance.now();
  const res = await request(`${API_BASE}/predict${query}`, {
    method: 'POST',
    body: form,
    signal,
  });
  let text: string;
  try {
    text = await res.text();
  } catch (err) {
    throw toApiError(err);
  }
  const roundTripMs = performance.now() - started;
  let data: PredictResponse;
  try {
    data = JSON.parse(text) as PredictResponse;
  } catch {
    throw new ApiError('server', 'The server returned an unreadable response.');
  }
  return { data, roundTripMs };
}

/** GET /api/nutrition/{dish}?servings= */
export async function getNutrition(
  dish: string,
  servings = 1,
  signal?: AbortSignal,
): Promise<Nutrition> {
  const res = await request(
    `${API_BASE}/nutrition/${encodeURIComponent(dish)}${buildQuery({ servings })}`,
    { signal },
  );
  return (await res.json()) as Nutrition;
}

/** GET /api/health */
export async function getHealth(signal?: AbortSignal): Promise<Health> {
  const res = await request(`${API_BASE}/health`, { signal });
  return (await res.json()) as Health;
}
