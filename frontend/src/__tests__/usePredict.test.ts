import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { initialPredictState, predictReducer, usePredict } from '../hooks/usePredict';
import type { PredictResponse } from '../lib/types';

const file = new File([new Uint8Array([1, 2, 3])], 'meal.jpg', { type: 'image/jpeg' });

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const okBody: PredictResponse = {
  top1: { label: 'pizza', display_name: 'Pizza', confidence: 0.9 },
  topk: [{ label: 'pizza', display_name: 'Pizza', confidence: 0.9 }],
  triage: { level: 'confident', message: 'High confidence prediction.', alternatives_with_nutrition: [] },
  nutrition: {
    dish: 'pizza',
    display_name: 'Pizza',
    serving_description: '1 slice',
    servings: 1,
    calories_kcal: 285,
    protein_g: 12,
    carbs_g: 36,
    fat_g: 10,
    fiber_g: 2.5,
    macro_energy_split: { protein_pct: 16.8, carbs_pct: 50.5, fat_pct: 32.7 },
    source: 'usda_approx',
  },
  gradcam: null,
  latency: {
    preprocess_ms: 1,
    inference_ms: 2,
    gradcam_ms: null,
    postprocess_ms: 3,
    total_ms: 6,
    classification_path_ms: 6,
  },
  engine: 'onnx_fp32',
  model_version: 'test',
  image: { original_width: 100, original_height: 80 },
};

async function runAnalyze(mock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('fetch', mock);
  const hook = renderHook(() => usePredict({ debounceMs: 0 }));
  act(() => hook.result.current.analyze(file));
  await waitFor(() => expect(hook.result.current.state.status).not.toBe('loading'));
  return hook;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('usePredict error mapping', () => {
  it('maps 503 to model_unavailable', async () => {
    const { result } = await runAnalyze(
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Model artifacts not found.', code: 'model_unavailable' }, 503)),
    );
    expect(result.current.state.status).toBe('error');
    expect(result.current.state.error?.kind).toBe('model_unavailable');
    expect(result.current.state.error?.status).toBe(503);
    expect(result.current.state.error?.detail).toBe('Model artifacts not found.');
  });

  it('maps 413 to too_large', async () => {
    const { result } = await runAnalyze(
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Too big' }, 413)),
    );
    expect(result.current.state.error?.kind).toBe('too_large');
  });

  it('maps 415 and 422', async () => {
    const a = await runAnalyze(vi.fn().mockResolvedValue(jsonResponse({ detail: 'x' }, 415)));
    expect(a.result.current.state.error?.kind).toBe('unsupported_type');
    const b = await runAnalyze(vi.fn().mockResolvedValue(jsonResponse({ detail: 'x' }, 422)));
    expect(b.result.current.state.error?.kind).toBe('invalid_image');
  });

  it('maps a failed fetch to network', async () => {
    const { result } = await runAnalyze(vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    expect(result.current.state.status).toBe('error');
    expect(result.current.state.error?.kind).toBe('network');
  });

  it('tolerates non-JSON error bodies', async () => {
    const { result } = await runAnalyze(
      vi.fn().mockResolvedValue(new Response('boom', { status: 500 })),
    );
    expect(result.current.state.error?.kind).toBe('server');
  });
});

describe('usePredict success and cancel', () => {
  it('stores the result and a measured round trip', async () => {
    const mock = vi.fn().mockResolvedValue(jsonResponse(okBody, 200));
    const { result } = await runAnalyze(mock);
    expect(result.current.state.status).toBe('success');
    expect(result.current.state.result?.top1.label).toBe('pizza');
    expect(result.current.state.roundTripMs).toBeGreaterThanOrEqual(0);
    const url = mock.mock.calls[0][0] as string;
    expect(url).toContain('/api/predict');
    expect(url).toContain('top_k=3');
  });

  it('cancel aborts the in-flight request and returns to idle', async () => {
    let aborted = false;
    const mock = vi.fn((_url: string, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          aborted = true;
          reject(new DOMException('Aborted', 'AbortError'));
        });
      }),
    );
    vi.stubGlobal('fetch', mock);
    const { result } = renderHook(() => usePredict({ debounceMs: 0 }));
    act(() => result.current.analyze(file));
    expect(result.current.state.status).toBe('loading');
    act(() => result.current.cancel());
    expect(aborted).toBe(true);
    expect(result.current.state.status).toBe('idle');
    expect(result.current.state.error).toBeNull();
  });
});

describe('predictReducer', () => {
  it('resets alternative view on a new start', () => {
    const withView = {
      ...initialPredictState,
      status: 'success' as const,
      viewLoading: 'x',
    };
    const next = predictReducer(withView, { type: 'start', file });
    expect(next.status).toBe('loading');
    expect(next.viewLoading).toBeNull();
    expect(next.file).toBe(file);
  });
});
