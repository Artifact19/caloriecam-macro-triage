import { useId, useState } from 'react';
import { Info, Layers, Image as ImageIcon, Loader2 } from 'lucide-react';
import type { Gradcam } from '../lib/types';

interface HeatmapViewerProps {
  originalUrl: string;
  /** Original image dimensions (used for the aspect-ratio box so overlays align exactly). */
  width: number;
  height: number;
  gradcam: Gradcam | null;
  /** Display name of the class being explained. */
  targetName?: string;
  /** True while a new heatmap is being fetched (alternative selected). */
  busy?: boolean;
}

type Tab = 'original' | 'attention';

const LEGEND_GRADIENT = 'linear-gradient(90deg, #0000ff, #00ffff, #00ff00, #ffff00, #ff0000)';

export function HeatmapViewer({
  originalUrl,
  width,
  height,
  gradcam,
  targetName,
  busy = false,
}: HeatmapViewerProps) {
  const [opacity, setOpacity] = useState(55);
  const [tab, setTab] = useState<Tab>('attention');
  const [showInfo, setShowInfo] = useState(false);
  const sliderId = useId();
  const infoId = useId();
  const aspectRatio = `${Math.max(1, width)} / ${Math.max(1, height)}`;

  const originalPanel = (
    <figure className={`${tab === 'original' ? 'block' : 'hidden'} md:block`}>
      <div
        className="relative w-full overflow-hidden rounded-xl border-2 border-ink bg-sunken"
        style={{ aspectRatio }}
      >
        <img
          src={originalUrl}
          alt="Original meal"
          className="absolute inset-0 h-full w-full object-contain"
        />
      </div>
      <figcaption className="mt-2 text-sm font-bold">Original</figcaption>
    </figure>
  );

  const attentionPanel = (
    <figure className={`${tab === 'attention' ? 'block' : 'hidden'} md:block`}>
      <div
        className="relative w-full overflow-hidden rounded-xl border-2 border-ink bg-sunken"
        style={{ aspectRatio }}
      >
        <img
          src={originalUrl}
          alt=""
          aria-hidden="true"
          className="absolute inset-0 h-full w-full object-contain"
        />
        {gradcam ? (
          <img
            src={`data:image/png;base64,${gradcam.heatmap_png_base64}`}
            alt={`Grad-CAM attention heatmap${targetName ? ` for ${targetName}` : ''}`}
            data-testid="heatmap-overlay"
            className="absolute inset-0 h-full w-full object-contain transition-opacity duration-150 motion-reduce:transition-none"
            style={{ opacity: opacity / 100 }}
          />
        ) : (
          <div
            className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-surface/90 p-4 text-center"
            data-testid="heatmap-placeholder"
          >
            <ImageIcon size={28} strokeWidth={2.5} aria-hidden="true" />
            <p className="text-sm font-bold">Attention map unavailable</p>
            <p className="text-xs text-muted">
              Grad-CAM was disabled or failed for this request. The prediction is still valid.
            </p>
          </div>
        )}
        {busy && (
          <div className="absolute inset-0 flex items-center justify-center bg-surface/70" role="status">
            <span className="tag-pill bg-sun">
              <Loader2 size={14} className="animate-spin motion-reduce:animate-none" aria-hidden="true" />
              Updating attention&hellip;
            </span>
          </div>
        )}
      </div>
      <figcaption className="mt-2 flex items-center gap-2 text-sm font-bold">
        Grad-CAM attention{targetName ? ` \u00b7 ${targetName}` : ''}
        <button
          type="button"
          aria-expanded={showInfo}
          aria-controls={infoId}
          aria-label="What is Grad-CAM?"
          title="Grad-CAM highlights the image regions that most influenced the model's decision."
          onClick={() => setShowInfo((s) => !s)}
          className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-ink bg-sun text-night"
        >
          <Info size={16} strokeWidth={2.5} aria-hidden="true" />
        </button>
      </figcaption>
    </figure>
  );

  return (
    <div className="brutal-card p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-display text-lg font-bold">
          <Layers size={20} strokeWidth={2.5} aria-hidden="true" />
          What the model looked at
        </h2>
      </div>

      {/* Tabs (mobile only) */}
      <div role="tablist" aria-label="Image view" className="mb-3 flex overflow-hidden rounded-xl border-2 border-ink shadow-brutal-sm md:hidden">
        {(['original', 'attention'] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`min-h-[44px] flex-1 px-3 font-display text-sm font-bold text-night ${
              tab === t ? 'bg-sun' : 'bg-surface !text-ink'
            } ${t === 'original' ? 'border-r-2 border-ink' : ''}`}
          >
            {t === 'original' ? 'Original' : 'Attention'}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {originalPanel}
        {attentionPanel}
      </div>

      {showInfo && (
        <p
          id={infoId}
          className="mt-3 rounded-xl border-2 border-ink bg-sun p-3 text-sm font-medium text-night"
        >
          Grad-CAM highlights the image regions that most influenced the model&apos;s decision for the
          selected class.
        </p>
      )}

      {gradcam && (
        <div className="mt-4 space-y-3">
          <div>
            <label htmlFor={sliderId} className="flex items-center justify-between text-sm font-bold">
              <span>Heatmap opacity</span>
              <span className="tabular rounded-full border-2 border-ink bg-grape px-2 text-night">
                {opacity}%
              </span>
            </label>
            <input
              id={sliderId}
              type="range"
              min={0}
              max={100}
              step={1}
              value={opacity}
              aria-label="Heatmap opacity"
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="range-brutal"
            />
          </div>
          <div>
            <div
              className="h-4 w-full rounded-full border-2 border-ink"
              style={{ background: LEGEND_GRADIENT }}
              role="img"
              aria-label="Legend: blue is low attention, red is high attention"
            />
            <div className="mt-1 flex justify-between text-xs font-bold">
              <span>Low attention</span>
              <span>High attention</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
