import { useEffect, useMemo, useState } from 'react';
import { Dashboard } from './components/Dashboard';
import { ConnectionBanner } from './components/ConnectionBanner';
import { EmptyPanel, Hero } from './components/Hero';
import { ErrorState } from './components/ErrorState';
import { Header } from './components/Header';
import { SampleGallery } from './components/SampleGallery';
import { Skeletons } from './components/Skeletons';
import { UploadZone } from './components/UploadZone';
import { useDarkMode } from './hooks/useDarkMode';
import { useHealth } from './hooks/useHealth';
import { usePredict } from './hooks/usePredict';
import { describeApiError } from './lib/errors';

export default function App() {
  const { dark, toggle } = useDarkMode();
  const { status: backendStatus, health, recheck } = useHealth();
  const { state, analyze, reanalyze, cancel, reset, viewAlternative, clearAlternative } =
    usePredict();
  const [selectedSample, setSelectedSample] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const file = state.file;
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const announcement = useMemo(() => {
    if (state.status === 'loading') return 'Analyzing meal\u2026';
    if (state.status === 'error' && state.error) {
      const copy = describeApiError(state.error);
      return `${copy.title}. ${copy.message}`;
    }
    if (state.status === 'success' && state.result) {
      const r = state.result;
      const shown = state.view ? state.view.nutrition : r.nutrition;
      const name = state.view ? `Viewing alternative ${state.view.display_name}` : r.top1.display_name;
      return `Result: ${name}. Top prediction ${r.top1.display_name} at ${Math.round(
        r.top1.confidence * 100,
      )} percent confidence. About ${Math.round(shown.calories_kcal)} kilocalories per serving.`;
    }
    return '';
  }, [state.status, state.error, state.result, state.view]);

  const handleFile = (f: File, sampleId: string | null = null) => {
    setSelectedSample(sampleId);
    analyze(f);
  };

  const handleRemove = () => {
    setSelectedSample(null);
    reset();
  };

  const busy = state.status === 'loading';

  return (
    <div className="min-h-screen pb-10">
      <Header dark={dark} onToggleDark={toggle} backendStatus={backendStatus} />
      <ConnectionBanner status={backendStatus} health={health} onRetry={() => void recheck()} />

      <div aria-live="polite" role="status" className="sr-only" data-testid="live-region">
        {announcement}
      </div>

      <main className="mx-auto mt-6 w-full max-w-6xl space-y-6 px-4 sm:px-6">
        {state.status === 'idle' && !state.file && <Hero />}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-start">
          <div className="space-y-6">
            <UploadZone
              file={state.file}
              previewUrl={previewUrl}
              busy={busy}
              onFile={(f) => handleFile(f, null)}
              onRemove={handleRemove}
              onReanalyze={reanalyze}
            />
            <SampleGallery
              selectedId={selectedSample}
              onSelect={(f, id) => handleFile(f, id)}
            />
          </div>

          <section aria-label="Results" className="min-w-0">
            {state.status === 'loading' && <Skeletons onCancel={cancel} />}
            {state.status === 'error' && state.error && (
              <ErrorState error={state.error} onRetry={reanalyze} onDismiss={handleRemove} />
            )}
            {state.status === 'success' && state.result && previewUrl && (
              <Dashboard
                state={state}
                previewUrl={previewUrl}
                onReanalyze={reanalyze}
                onSelectAlternative={viewAlternative}
                onClearAlternative={clearAlternative}
              />
            )}
            {state.status === 'idle' && <EmptyPanel />}
          </section>
        </div>
      </main>

      <footer className="mx-auto mt-10 w-full max-w-6xl px-4 sm:px-6">
        <p className="rounded-xl border-2 border-ink bg-surface px-4 py-3 text-center text-sm font-bold shadow-brutal-sm">
          Estimates are approximate and not medical advice.
        </p>
      </footer>
    </div>
  );
}
