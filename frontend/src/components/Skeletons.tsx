import { X } from 'lucide-react';

function Block({ className = '' }: { className?: string }) {
  return <div aria-hidden="true" className={`skeleton ${className}`} />;
}

interface SkeletonsProps {
  onCancel: () => void;
}

/** Loading placeholder mirroring the dashboard, with an indeterminate progress bar and Cancel. */
export function Skeletons({ onCancel }: SkeletonsProps) {
  return (
    <div className="space-y-5" aria-busy="true" data-testid="skeletons">
      <div className="brutal-card space-y-3 p-4 sm:p-5">
        <div className="flex items-center justify-between gap-3">
          <p className="font-display text-lg font-bold">Analyzing your meal&hellip;</p>
          <button type="button" className="btn-brutal bg-surface !text-ink" onClick={onCancel}>
            <X size={18} strokeWidth={2.5} aria-hidden="true" />
            Cancel
          </button>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-label="Analyzing meal"
          aria-valuetext="In progress"
        >
          <div className="progress-stripes h-full w-full animate-stripes bg-coral motion-reduce:animate-none" />
        </div>
      </div>

      <div className="brutal-card grid gap-4 p-4 sm:grid-cols-2 sm:p-5">
        <div className="space-y-3">
          <Block className="h-8 w-2/3" />
          <Block className="h-4 w-1/3" />
        </div>
        <Block className="h-28" />
      </div>

      <div className="brutal-card p-4 sm:p-5">
        <Block className="mb-3 h-6 w-1/2" />
        <div className="grid gap-4 md:grid-cols-2">
          <Block className="aspect-[4/3]" />
          <Block className="aspect-[4/3]" />
        </div>
      </div>

      <div className="brutal-card space-y-4 p-4 sm:p-5">
        <Block className="h-14 w-1/2" />
        <div className="grid grid-cols-3 gap-3">
          <Block className="h-24 rounded-full" />
          <Block className="h-24 rounded-full" />
          <Block className="h-24 rounded-full" />
        </div>
        <Block className="h-8" />
      </div>
    </div>
  );
}
