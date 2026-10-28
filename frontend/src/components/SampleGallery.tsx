import { useState } from 'react';
import { Check, ImageOff } from 'lucide-react';

export interface SampleDef {
  id: string;
  label: string;
  /** Expected class from the spec mapping (informational). */
  dish: string;
  src: string;
  color: string;
}

export const SAMPLES: SampleDef[] = [
  { id: 'pizza', label: 'Pizza', dish: 'pizza', src: '/samples/pizza.jpg', color: 'bg-coral' },
  { id: 'salad', label: 'Salad', dish: 'greek_salad', src: '/samples/salad.jpg', color: 'bg-teal' },
  { id: 'steak', label: 'Steak', dish: 'steak', src: '/samples/steak.jpg', color: 'bg-tangerine' },
  { id: 'curry', label: 'Curry', dish: 'chicken_curry', src: '/samples/curry.jpg', color: 'bg-sun' },
];

interface SampleGalleryProps {
  selectedId: string | null;
  disabled?: boolean;
  onSelect: (file: File, sampleId: string) => void;
}

export function SampleGallery({ selectedId, disabled = false, onSelect }: SampleGalleryProps) {
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [failed, setFailed] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  const choose = async (sample: SampleDef) => {
    setError(null);
    setLoadingId(sample.id);
    try {
      const res = await fetch(sample.src);
      const blob = await res.blob();
      // The dev server may answer a missing static file with index.html (HTTP 200).
      if (!res.ok || !blob.type.startsWith('image/')) {
        throw new Error('missing');
      }
      const file = new File([blob], `${sample.id}.jpg`, { type: blob.type });
      onSelect(file, sample.id);
    } catch {
      setError(
        `Couldn't load the ${sample.label} sample. Generate samples with scripts/make_samples.py or upload your own photo.`,
      );
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <section aria-label="Sample meals" className="space-y-3">
      <h2 className="font-display text-lg font-bold">Or try a sample</h2>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-2 xl:grid-cols-4">
        {SAMPLES.map((sample) => {
          const selected = selectedId === sample.id;
          return (
            <li key={sample.id}>
              <button
                type="button"
                aria-pressed={selected}
                disabled={disabled || loadingId !== null}
                onClick={() => void choose(sample)}
                className={`group relative block w-full overflow-hidden rounded-xl border-2 border-ink text-left text-night transition-all duration-100 motion-reduce:transition-none ${sample.color} ${
                  selected
                    ? 'translate-x-[2px] translate-y-[2px] shadow-brutal-sm ring-4 ring-grape ring-offset-2 ring-offset-page'
                    : 'shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-brutal-sm active:translate-x-[4px] active:translate-y-[4px] active:shadow-brutal-none'
                } disabled:opacity-60`}
              >
                <span className="relative flex aspect-[4/3] w-full items-center justify-center border-b-2 border-ink">
                  {failed[sample.id] ? (
                    <ImageOff size={28} strokeWidth={2.5} aria-hidden="true" />
                  ) : (
                    <img
                      src={sample.src}
                      alt=""
                      loading="lazy"
                      className="h-full w-full object-cover"
                      onError={() => setFailed((f) => ({ ...f, [sample.id]: true }))}
                    />
                  )}
                  {selected && (
                    <span className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full border-2 border-ink bg-teal">
                      <Check size={14} strokeWidth={3.5} aria-hidden="true" />
                    </span>
                  )}
                </span>
                <span className="flex min-h-[44px] items-center px-3 font-display text-sm font-bold">
                  {loadingId === sample.id ? 'Loading\u2026' : sample.label}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {error && (
        <p
          role="alert"
          className="rounded-xl border-2 border-ink bg-sun px-3 py-2 text-sm font-bold text-night shadow-brutal-sm"
        >
          {error}
        </p>
      )}
    </section>
  );
}
