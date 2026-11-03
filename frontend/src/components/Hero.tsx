import { Camera, ClipboardPaste, Gauge, ScanSearch } from 'lucide-react';
import { CircleShape, DiamondShape, SparkleShape, SquareShape, StarShape, TriangleShape } from './Decor';

/** Empty-state hero with decorative shapes. */
export function Hero() {
  return (
    <section
      aria-label="Welcome"
      className="relative overflow-hidden rounded-3xl border-2 border-ink bg-surface px-5 py-10 text-center shadow-brutal-lg sm:px-10 sm:py-14"
    >
      <StarShape className="absolute left-[8%] top-[14%] animate-bob motion-reduce:animate-none" size={26} />
      <TriangleShape className="absolute right-[10%] top-[12%] animate-bob motion-reduce:animate-none" size={22} color="#8C9B7A" rotate={25} />
      <DiamondShape className="absolute bottom-[16%] left-[12%] animate-bob motion-reduce:animate-none" size={22} />
      <TriangleShape className="absolute bottom-[14%] right-[9%] animate-bob motion-reduce:animate-none" size={20} color="#DC903C" rotate={-15} />
      <SquareShape className="absolute left-[20%] bottom-[8%] animate-bob motion-reduce:animate-none" size={18} />
      <CircleShape className="absolute right-[22%] top-[8%] animate-bob motion-reduce:animate-none" size={20} />
      <SparkleShape className="absolute right-[30%] bottom-[12%] text-ink" size={14} color="var(--c-ink)" />

      <span
        aria-hidden="true"
        className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border-2 border-ink bg-tangerine text-night shadow-brutal"
      >
        <ScanSearch size={32} strokeWidth={2.5} />
      </span>
      <h2 className="mx-auto max-w-2xl font-display text-4xl font-bold leading-[1.05] sm:text-6xl">
        Snap a meal.
        <br />
        <span className="text-muted">Know the macros.</span>
      </h2>
      <p className="mx-auto mt-4 max-w-xl text-base font-medium text-muted sm:text-lg">
        Drop, paste or photograph any of our 25 supported dishes. CalorieCAM identifies the meal, highlights the plate, and provides instant nutritional estimates.
      </p>
      <ul className="mt-6 flex flex-wrap items-center justify-center gap-2">
        <li className="tag-pill bg-coral">25 Classic Dishes</li>
        <li className="tag-pill bg-teal">Visual Focus Heatmap</li>
        <li className="tag-pill bg-sun">Private &amp; On-Device</li>
        <li className="tag-pill bg-tangerine">Instant Nutrition Breakdown</li>
      </ul>

      <div className="mx-auto mt-6 flex items-center justify-center gap-2 text-xs font-bold text-muted">
        <span className="flex text-tangerine" aria-hidden="true">★★★★★</span>
        <span>5/5 on-device accuracy</span>
        <span>&middot;</span>
        <span>Zero cloud data leaks</span>
      </div>
    </section>
  );
}

/** Right-column placeholder shown before an image is chosen. */
export function EmptyPanel() {
  const steps = [
    { icon: Camera, title: 'Add a photo', text: 'Upload, paste, snap, or choose a sample plate.', color: 'bg-sun' },
    { icon: Gauge, title: 'Instant recognition', text: 'Dish match, confidence score, and meal alternatives.', color: 'bg-teal' },
    { icon: ClipboardPaste, title: 'Adjust portions', text: 'Tweak servings and see calories & macros update live.', color: 'bg-grape' },
  ];
  return (
    <section
      aria-label="How it works"
      className="rounded-2xl border-2 border-ink bg-panel p-5 shadow-brutal sm:p-6"
      data-testid="empty-panel"
    >
      <h2 className="font-display text-xl font-bold">How it works</h2>
      <ol className="mt-4 space-y-3">
        {steps.map(({ icon: Icon, title, text, color }, i) => (
          <li
            key={title}
            className="flex items-center gap-3 rounded-xl border-2 border-ink bg-surface p-3 shadow-brutal-sm"
          >
            <span
              aria-hidden="true"
              className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border-2 border-ink text-night ${color}`}
            >
              <Icon size={22} strokeWidth={2.5} />
            </span>
            <div>
              <p className="font-display font-bold">
                {i + 1}. {title}
              </p>
              <p className="text-sm text-muted">{text}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
