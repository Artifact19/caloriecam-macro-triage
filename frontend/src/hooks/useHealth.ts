import { useCallback, useEffect, useRef, useState } from 'react';
import { getHealth } from '../lib/api';
import type { Health } from '../lib/types';

export type BackendStatus = 'checking' | 'ok' | 'unreachable' | 'no_model';

/**
 * Polls /api/health on load. While the backend is unreachable or has no model it keeps
 * polling every `intervalMs`; once healthy it stops.
 */
export function useHealth(intervalMs = 5000) {
  const [status, setStatus] = useState<BackendStatus>('checking');
  const [health, setHealth] = useState<Health | null>(null);
  const timerRef = useRef<number | undefined>(undefined);
  const stoppedRef = useRef(false);

  const check = useCallback(async () => {
    window.clearTimeout(timerRef.current);
    try {
      const h = await getHealth();
      if (stoppedRef.current) return;
      setHealth(h);
      if (h.model_loaded) {
        setStatus('ok');
        return;
      }
      setStatus('no_model');
    } catch {
      if (stoppedRef.current) return;
      setHealth(null);
      setStatus('unreachable');
    }
    timerRef.current = window.setTimeout(() => void check(), intervalMs);
  }, [intervalMs]);

  useEffect(() => {
    stoppedRef.current = false;
    void check();
    return () => {
      stoppedRef.current = true;
      window.clearTimeout(timerRef.current);
    };
  }, [check]);

  return { status, health, recheck: check };
}
