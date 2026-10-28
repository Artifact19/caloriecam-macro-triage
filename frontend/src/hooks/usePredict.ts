import { useCallback, useEffect, useReducer, useRef } from 'react';
import { getNutrition, predict } from '../lib/api';
import { ApiError, toApiError } from '../lib/errors';
import { nutritionFromAlternative } from '../lib/format';
import type {
  AlternativeWithNutrition,
  Gradcam,
  Nutrition,
  PredictResponse,
} from '../lib/types';

export type PredictStatus = 'idle' | 'loading' | 'success' | 'error';

/** A triage alternative the user is currently inspecting. */
export interface AlternativeView {
  label: string;
  display_name: string;
  confidence: number;
  nutrition: Nutrition;
  gradcam: Gradcam | null;
}

export interface PredictState {
  status: PredictStatus;
  file: File | null;
  result: PredictResponse | null;
  /** Client-measured round trip (performance.now()) for the main prediction. */
  roundTripMs: number | null;
  error: ApiError | null;
  view: AlternativeView | null;
  /** Label of the alternative currently being fetched. */
  viewLoading: string | null;
  viewError: ApiError | null;
}

export type PredictAction =
  | { type: 'start'; file: File }
  | { type: 'success'; result: PredictResponse; roundTripMs: number }
  | { type: 'failure'; error: ApiError }
  | { type: 'cancel' }
  | { type: 'reset' }
  | { type: 'viewStart'; label: string }
  | { type: 'viewSuccess'; view: AlternativeView }
  | { type: 'viewFailure'; error: ApiError }
  | { type: 'viewClear' };

export const initialPredictState: PredictState = {
  status: 'idle',
  file: null,
  result: null,
  roundTripMs: null,
  error: null,
  view: null,
  viewLoading: null,
  viewError: null,
};

export function predictReducer(state: PredictState, action: PredictAction): PredictState {
  switch (action.type) {
    case 'start':
      return { ...initialPredictState, status: 'loading', file: action.file };
    case 'success':
      return {
        ...state,
        status: 'success',
        result: action.result,
        roundTripMs: action.roundTripMs,
        error: null,
      };
    case 'failure':
      return { ...state, status: 'error', error: action.error, result: null, roundTripMs: null };
    case 'cancel':
      return {
        ...state,
        status: state.status === 'loading' ? 'idle' : state.status,
        viewLoading: null,
      };
    case 'reset':
      return initialPredictState;
    case 'viewStart':
      return { ...state, viewLoading: action.label, viewError: null };
    case 'viewSuccess':
      return { ...state, view: action.view, viewLoading: null, viewError: null };
    case 'viewFailure':
      return { ...state, viewLoading: null, viewError: action.error };
    case 'viewClear':
      return { ...state, view: null, viewLoading: null, viewError: null };
    default:
      return state;
  }
}

export interface UsePredictOptions {
  /** Delay before auto-run fires after a new image is selected. Default 150 ms. */
  debounceMs?: number;
}

export function usePredict(options: UsePredictOptions = {}) {
  const debounceMs = options.debounceMs ?? 150;
  const [state, dispatch] = useReducer(predictReducer, initialPredictState);
  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<number | undefined>(undefined);
  const fileRef = useRef<File | null>(null);
  const resultRef = useRef<PredictResponse | null>(null);

  useEffect(() => {
    resultRef.current = state.result;
  }, [state.result]);

  const abortInFlight = useCallback(() => {
    window.clearTimeout(timerRef.current);
    timerRef.current = undefined;
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  useEffect(() => abortInFlight, [abortInFlight]);

  const analyze = useCallback(
    (file: File) => {
      abortInFlight();
      fileRef.current = file;
      dispatch({ type: 'start', file });
      const controller = new AbortController();
      abortRef.current = controller;

      const exec = async () => {
        try {
          const { data, roundTripMs } = await predict(
            file,
            { top_k: 3, gradcam: true, servings: 1 },
            controller.signal,
          );
          if (controller.signal.aborted) return;
          dispatch({ type: 'success', result: data, roundTripMs });
        } catch (err) {
          if (controller.signal.aborted) return;
          dispatch({ type: 'failure', error: toApiError(err) });
        }
      };

      if (debounceMs > 0) {
        timerRef.current = window.setTimeout(() => void exec(), debounceMs);
      } else {
        void exec();
      }
    },
    [abortInFlight, debounceMs],
  );

  const reanalyze = useCallback(() => {
    if (fileRef.current) analyze(fileRef.current);
  }, [analyze]);

  const cancel = useCallback(() => {
    abortInFlight();
    dispatch({ type: 'cancel' });
  }, [abortInFlight]);

  const reset = useCallback(() => {
    abortInFlight();
    fileRef.current = null;
    dispatch({ type: 'reset' });
  }, [abortInFlight]);

  const clearAlternative = useCallback(() => {
    abortInFlight();
    dispatch({ type: 'viewClear' });
  }, [abortInFlight]);

  /** Swap nutrition to an alternative and re-request Grad-CAM for that class. */
  const viewAlternative = useCallback(
    (alt: AlternativeWithNutrition) => {
      const file = fileRef.current;
      const result = resultRef.current;
      if (!file || !result) return;
      if (alt.label === result.top1.label) {
        clearAlternative();
        return;
      }
      abortInFlight();
      const controller = new AbortController();
      abortRef.current = controller;
      dispatch({ type: 'viewStart', label: alt.label });

      const embedded = nutritionFromAlternative(alt);
      const nutritionPromise: Promise<Nutrition> = embedded
        ? Promise.resolve(embedded)
        : getNutrition(alt.label, 1, controller.signal);
      const gradcamPromise: Promise<Gradcam | null> = predict(
        file,
        { top_k: 3, gradcam: true, servings: 1, gradcam_class: alt.label },
        controller.signal,
      ).then(
        (r) => r.data.gradcam,
        (err: unknown) => {
          if (controller.signal.aborted) throw err;
          return null; // heatmap is optional: degrade gracefully
        },
      );

      Promise.all([nutritionPromise, gradcamPromise])
        .then(([nutrition, gradcam]) => {
          if (controller.signal.aborted) return;
          dispatch({
            type: 'viewSuccess',
            view: {
              label: alt.label,
              display_name: alt.display_name,
              confidence: alt.confidence,
              nutrition,
              gradcam,
            },
          });
        })
        .catch((err: unknown) => {
          if (controller.signal.aborted) return;
          dispatch({ type: 'viewFailure', error: toApiError(err) });
        });
    },
    [abortInFlight, clearAlternative],
  );

  return { state, analyze, reanalyze, cancel, reset, viewAlternative, clearAlternative };
}
