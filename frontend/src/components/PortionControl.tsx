import { useState } from 'react';
import { Minus, Plus } from 'lucide-react';

interface PortionControlProps {
  value: number;
  onChange: (servings: number) => void;
}

const PRESETS = [0.5, 1, 1.5, 2] as const;
const MIN = 0.25;
const MAX = 10;

function label(v: number): string {
  return `${v}\u00d7`;
}

export function PortionControl({ value, onChange }: PortionControlProps) {
  const [custom, setCustom] = useState(false);
  const [draft, setDraft] = useState<string | null>(null);
  const isPreset = (PRESETS as readonly number[]).includes(value);
  const customActive = custom || !isPreset;

  const clamp = (v: number) => Math.min(MAX, Math.max(MIN, Math.round(v * 100) / 100));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span id="portion-label" className="font-display text-sm font-bold">
          Portion size
        </span>
        <span className="tabular tag-pill bg-sun" aria-live="polite">
          {label(value)}
        </span>
      </div>
      <div
        role="group"
        aria-labelledby="portion-label"
        className="flex overflow-hidden rounded-xl border-2 border-ink shadow-brutal-sm"
      >
        {PRESETS.map((p) => {
          const active = !customActive && value === p;
          return (
            <button
              key={p}
              type="button"
              aria-pressed={active}
              onClick={() => {
                setCustom(false);
                onChange(p);
              }}
              className={`min-h-[44px] min-w-0 flex-1 border-r-2 border-ink px-2 font-display text-sm font-bold ${
                active ? 'bg-coral text-night' : 'bg-surface text-ink'
              }`}
            >
              {label(p)}
            </button>
          );
        })}
        <button
          type="button"
          aria-pressed={customActive}
          onClick={() => setCustom(true)}
          className={`min-h-[44px] min-w-0 flex-1 px-2 font-display text-sm font-bold ${
            customActive ? 'bg-coral text-night' : 'bg-surface text-ink'
          }`}
        >
          Custom
        </button>
      </div>

      {customActive && (
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="Decrease servings"
            className="btn-brutal h-11 w-11 !px-0 bg-surface !text-ink"
            onClick={() => onChange(clamp(value - 0.25))}
          >
            <Minus size={18} strokeWidth={3} aria-hidden="true" />
          </button>
          <input
            type="number"
            inputMode="decimal"
            aria-label="Custom servings"
            min={MIN}
            max={MAX}
            step={0.25}
            value={draft ?? String(value)}
            onChange={(e) => {
              setDraft(e.target.value);
              const n = parseFloat(e.target.value);
              if (Number.isFinite(n) && n >= MIN && n <= MAX) onChange(n);
            }}
            onBlur={() => {
              const n = parseFloat(draft ?? '');
              if (Number.isFinite(n)) onChange(clamp(n));
              setDraft(null);
            }}
            className="input-brutal tabular w-24 text-center font-bold"
          />
          <button
            type="button"
            aria-label="Increase servings"
            className="btn-brutal h-11 w-11 !px-0 bg-surface !text-ink"
            onClick={() => onChange(clamp(value + 0.25))}
          >
            <Plus size={18} strokeWidth={3} aria-hidden="true" />
          </button>
          <span className="text-xs font-medium text-muted">
            {MIN} to {MAX} servings
          </span>
        </div>
      )}
    </div>
  );
}
