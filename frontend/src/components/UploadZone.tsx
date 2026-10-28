import { useCallback, useEffect, useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, KeyboardEvent } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Camera, FolderOpen, ImagePlus, RefreshCw, Trash2, UploadCloud } from 'lucide-react';
import { formatBytes } from '../lib/format';
import { validateImageFile } from '../lib/validate';

interface UploadZoneProps {
  file: File | null;
  previewUrl: string | null;
  busy?: boolean;
  /** Called with a validated file. */
  onFile: (file: File) => void;
  onRemove: () => void;
  onReanalyze: () => void;
}

function useImageDimensions(url: string | null): { width: number; height: number } | null {
  const [dims, setDims] = useState<{ width: number; height: number } | null>(null);
  useEffect(() => {
    if (!url) {
      setDims(null);
      return;
    }
    let cancelled = false;
    const img = new Image();
    img.onload = () => {
      if (!cancelled) setDims({ width: img.naturalWidth, height: img.naturalHeight });
    };
    img.src = url;
    return () => {
      cancelled = true;
    };
  }, [url]);
  return dims;
}

export function UploadZone({
  file,
  previewUrl,
  busy = false,
  onFile,
  onRemove,
  onReanalyze,
}: UploadZoneProps) {
  const reduceMotion = useReducedMotion();
  const pickerRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dims = useImageDimensions(previewUrl);

  const accept = useCallback(
    (candidate: File | undefined | null) => {
      if (!candidate) return;
      const problem = validateImageFile(candidate);
      if (problem) {
        setError(problem);
        return;
      }
      setError(null);
      onFile(candidate);
    },
    [onFile],
  );

  // Clipboard paste (Ctrl/Cmd+V)
  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const items = event.clipboardData?.items;
      if (!items) return;
      for (const item of Array.from(items)) {
        if (item.kind === 'file' && item.type.startsWith('image/')) {
          const pasted = item.getAsFile();
          if (pasted) {
            event.preventDefault();
            const named =
              pasted.name && pasted.name !== 'image.png'
                ? pasted
                : new File([pasted], `pasted-${Date.now()}.${pasted.type.split('/')[1] || 'png'}`, {
                    type: pasted.type,
                  });
            accept(named);
            return;
          }
        }
      }
    };
    document.addEventListener('paste', onPaste);
    return () => document.removeEventListener('paste', onPaste);
  }, [accept]);

  const onInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    accept(event.target.files?.[0]);
    event.target.value = ''; // allow re-selecting the same file
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    accept(event.dataTransfer.files?.[0]);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      pickerRef.current?.click();
    }
  };

  return (
    <section aria-label="Image upload" className="space-y-3">
      <input
        ref={pickerRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        data-testid="file-input"
        onChange={onInputChange}
      />
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        data-testid="camera-input"
        onChange={onInputChange}
      />

      {file && previewUrl ? (
        <div className="brutal-card overflow-hidden">
          <div className="relative border-b-2 border-ink bg-sunken">
            <img
              src={previewUrl}
              alt={`Preview of ${file.name}`}
              className="mx-auto max-h-80 w-full object-contain"
            />
          </div>
          <div className="space-y-3 p-4">
            <div className="min-w-0">
              <p className="truncate font-display text-base font-bold" title={file.name}>
                {file.name}
              </p>
              <p className="tabular text-sm text-muted">
                {dims ? `${dims.width}\u00d7${dims.height} px \u00b7 ` : ''}
                {formatBytes(file.size)}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-brutal bg-sun"
                onClick={() => pickerRef.current?.click()}
              >
                <FolderOpen size={18} strokeWidth={2.5} aria-hidden="true" />
                Replace
              </button>
              <button
                type="button"
                className="btn-brutal bg-teal"
                onClick={onReanalyze}
                disabled={busy}
              >
                <RefreshCw size={18} strokeWidth={2.5} aria-hidden="true" />
                Re-analyze
              </button>
              <button type="button" className="btn-brutal bg-surface !text-ink" onClick={onRemove}>
                <Trash2 size={18} strokeWidth={2.5} aria-hidden="true" />
                Remove
              </button>
            </div>
          </div>
        </div>
      ) : (
        <motion.div
          role="button"
          tabIndex={0}
          aria-label="Upload a meal photo: drop an image here, click to browse, or paste from clipboard"
          onClick={() => pickerRef.current?.click()}
          onKeyDown={onKeyDown}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          animate={reduceMotion ? undefined : { scale: dragging ? 1.02 : 1, rotate: dragging ? -0.6 : 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 22 }}
          className={`flex min-h-[200px] cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-ink p-6 text-center shadow-brutal ${
            dragging ? 'bg-sun text-night' : 'bg-surface'
          }`}
        >
          <span
            aria-hidden="true"
            className="flex h-14 w-14 items-center justify-center rounded-xl border-2 border-ink bg-grape text-night shadow-brutal-sm"
          >
            {dragging ? <ImagePlus size={28} strokeWidth={2.5} /> : <UploadCloud size={28} strokeWidth={2.5} />}
          </span>
          <p className="font-display text-lg font-bold">
            {dragging ? 'Drop it!' : 'Drop a meal photo here'}
          </p>
          <p className="text-sm font-medium opacity-80">
            Click to browse, or paste with Ctrl/Cmd+V &middot; JPEG, PNG, WebP &middot; up to 10 MB
          </p>
        </motion.div>
      )}

      <div className="flex flex-wrap gap-3">
        {!file && (
          <button
            type="button"
            className="btn-brutal bg-sun"
            onClick={() => pickerRef.current?.click()}
          >
            <FolderOpen size={18} strokeWidth={2.5} aria-hidden="true" />
            Browse files
          </button>
        )}
        <button
          type="button"
          className="btn-brutal bg-coral"
          onClick={() => cameraRef.current?.click()}
        >
          <Camera size={18} strokeWidth={2.5} aria-hidden="true" />
          Take photo
        </button>
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-xl border-2 border-ink bg-coral px-3 py-2 text-sm font-bold text-night shadow-brutal-sm"
        >
          {error}
        </p>
      )}
    </section>
  );
}
