import { useId, useState } from 'react';
import { ChevronDown, Zap } from 'lucide-react';
import { formatEngine, formatMs } from '../lib/format';
import type { Latency } from '../lib/types';

interface TelemetryBadgeProps {
  latency: Latency;
  engine: string;
  modelVersion: string;
  /** Client-measured round trip (performance.now()) in ms. */
  roundTripMs: number | null;
}

/** Shows only measured values returned by the server and measured in the browser. */
export function TelemetryBadge({ latency, engine, modelVersion, roundTripMs }: TelemetryBadgeProps) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  const parts: { key: string; label: string; ms: number | null; color: string }[] = [
    { key: 'pre', label: 'Preprocess', ms: latency.preprocess_ms, color: '#A78BFA' },
    { key: 'inf', label: 'Inference', ms: latency.inference_ms, color: '#3CCBB9' },
    { key: 'gc', label: 'Grad-CAM', ms: latency.gradcam_ms, color: '#F25F5C' },
    { key: 'post', label: 'Postprocess', ms: latency.postprocess_ms, color: '#FFE066' },
  ];
  const sum = parts.reduce((acc, p) => acc + (p.ms ?? 0), 0);

  return (
    <div className="brutal-card">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
        className="flex min-h-[56px] w-full items-center justify-between gap-3 rounded-2xl px-4 py-3 text-left"
      >
        <span className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
          <span className="flex items-center gap-2 font-display font-bold">
            <Zap size={18} strokeWidth={2.5} className="text-tangerine" aria-hidden="true" />
            Ingest to Output:{' '}
            <span className="tabular" data-testid="total-ms">
              {formatMs(latency.total_ms)}
            </span>
          </span>
          <span className="tag-pill bg-grape">{formatEngine(engine)}</span>
        </span>
        <ChevronDown
          size={20}
          strokeWidth={3}
          aria-hidden="true"
          className={`shrink-0 transition-transform motion-reduce:transition-none ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div id={panelId} className="space-y-3 border-t-2 border-ink p-4 text-sm">
          {sum > 0 && (
            <div
              className="flex h-5 w-full overflow-hidden rounded-full border-2 border-ink"
              role="img"
              aria-label="Latency breakdown by stage"
            >
              {parts.map((p, i) => (
                <div
                  key={p.key}
                  style={{
                    width: `${((p.ms ?? 0) / sum) * 100}%`,
                    backgroundColor: p.color,
                  }}
                  className={i < parts.length - 1 ? 'border-r-2 border-ink' : ''}
                />
              ))}
            </div>
          )}
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
            {parts.map((p) => (
              <div key={p.key} className="contents">
                <dt className="flex items-center gap-2 font-medium">
                  <span
                    aria-hidden="true"
                    className="inline-block h-3 w-3 rounded-sm border-2 border-ink"
                    style={{ backgroundColor: p.color }}
                  />
                  {p.label}
                </dt>
                <dd className="tabular text-right font-bold">{formatMs(p.ms)}</dd>
              </div>
            ))}
            <dt className="border-t-2 border-dashed border-ink pt-1.5 font-medium">
              Classification only
            </dt>
            <dd className="tabular border-t-2 border-dashed border-ink pt-1.5 text-right font-bold">
              {formatMs(latency.classification_path_ms)}
            </dd>
            <dt className="font-medium">Server total</dt>
            <dd className="tabular text-right font-bold">{formatMs(latency.total_ms)}</dd>
            <dt className="font-medium">Round-trip (browser)</dt>
            <dd className="tabular text-right font-bold" data-testid="roundtrip-ms">
              {formatMs(roundTripMs)}
            </dd>
            <dt className="font-medium">Engine</dt>
            <dd className="text-right font-bold">{formatEngine(engine)}</dd>
            <dt className="font-medium">Model</dt>
            <dd className="break-all text-right font-bold">{modelVersion}</dd>
          </dl>
          <p className="text-xs text-muted">
            Server times are measured locally on the backend; round-trip is measured in your browser
            around the request.
          </p>
        </div>
      )}
    </div>
  );
}
