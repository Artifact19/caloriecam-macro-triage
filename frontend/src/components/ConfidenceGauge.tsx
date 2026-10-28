import { motion, useReducedMotion } from 'framer-motion';

interface ConfidenceGaugeProps {
  /** Confidence as a fraction 0..1. */
  confidence: number;
  className?: string;
}

export type ConfidenceBand = 'high' | 'medium' | 'low';

export function confidenceBand(confidence: number): ConfidenceBand {
  if (confidence >= 0.7) return 'high';
  if (confidence >= 0.4) return 'medium';
  return 'low';
}

const BAND_STYLE: Record<ConfidenceBand, { color: string; label: string }> = {
  high: { color: '#3CCBB9', label: 'High' },
  medium: { color: '#FFE066', label: 'Medium' },
  low: { color: '#F25F5C', label: 'Low' },
};

const ARC = 'M 14 62 A 46 46 0 0 1 106 62';

/** Semi-circular confidence gauge. Colour is paired with a text label (never the only signal). */
export function ConfidenceGauge({ confidence, className = '' }: ConfidenceGaugeProps) {
  const reduceMotion = useReducedMotion();
  const value = Math.min(1, Math.max(0, Number.isFinite(confidence) ? confidence : 0));
  const percent = Math.round(value * 100);
  const band = confidenceBand(value);
  const { color, label } = BAND_STYLE[band];

  return (
    <div
      role="meter"
      aria-label="Prediction confidence"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      aria-valuetext={`${percent} percent, ${label.toLowerCase()} confidence`}
      className={`relative mx-auto w-full max-w-[240px] ${className}`}
    >
      <svg viewBox="0 0 120 72" className="w-full" aria-hidden="true" focusable="false">
        {/* Ink outline */}
        <path d={ARC} fill="none" stroke="var(--c-ink)" strokeWidth="22" strokeLinecap="butt" />
        {/* Track */}
        <path d={ARC} fill="none" stroke="var(--c-sunken)" strokeWidth="14" strokeLinecap="butt" />
        {/* Value */}
        <motion.path
          d={ARC}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="butt"
          initial={{ pathLength: reduceMotion ? value : 0 }}
          animate={{ pathLength: value }}
          transition={{ duration: reduceMotion ? 0 : 1, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute inset-x-0 bottom-0 flex flex-col items-center leading-none">
        <span className="tabular font-display text-3xl font-bold" data-testid="confidence-value">
          {percent}%
        </span>
        <span className="mt-1 rounded-full border-2 border-ink px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-night" style={{ backgroundColor: color }}>
          {label}
        </span>
      </div>
    </div>
  );
}
