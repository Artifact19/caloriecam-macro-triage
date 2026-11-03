import { useState } from 'react';
import { ChevronDown, ChevronUp, Utensils } from 'lucide-react';

interface DishCategory {
  name: string;
  color: string;
  dishes: string[];
}

export const DISH_CATEGORIES: DishCategory[] = [
  {
    name: 'Mains & Italian',
    color: 'bg-coral',
    dishes: ['Pizza', 'Lasagna', 'Spaghetti Bolognese', 'Steak', 'Grilled Salmon'],
  },
  {
    name: 'Asian & Noodles',
    color: 'bg-sun',
    dishes: ['Chicken Curry', 'Ramen', 'Pad Thai', 'Fried Rice', 'Sushi'],
  },
  {
    name: 'Fast Food & Casual',
    color: 'bg-tangerine',
    dishes: ['Hamburger', 'Hot Dog', 'French Fries', 'Tacos', 'Samosa'],
  },
  {
    name: 'Salads & Dips',
    color: 'bg-teal',
    dishes: ['Caesar Salad', 'Greek Salad', 'Guacamole', 'Hummus'],
  },
  {
    name: 'Breakfast & Sweets',
    color: 'bg-grape',
    dishes: ['Omelette', 'Pancakes', 'Waffles', 'Donuts', 'Chocolate Cake', 'Ice Cream'],
  },
];

export function SupportedDishes() {
  const [open, setOpen] = useState(false);

  return (
    <div className="brutal-card overflow-hidden p-4 sm:p-5">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <div className="flex items-center gap-3">
          <span
            aria-hidden="true"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border-2 border-ink bg-sun text-night shadow-brutal-sm"
          >
            <Utensils size={20} strokeWidth={2.5} />
          </span>
          <div>
            <h3 className="font-display text-base font-bold sm:text-lg">
              25 Supported Dishes
            </h3>
            <p className="text-xs text-muted sm:text-sm">
              The model is trained to recognize these 25 specific meal categories.
            </p>
          </div>
        </div>
        <span className="btn-brutal h-9 px-3 text-xs bg-surface !text-ink">
          {open ? (
            <>
              Hide <ChevronUp size={16} strokeWidth={2.5} />
            </>
          ) : (
            <>
              View list <ChevronDown size={16} strokeWidth={2.5} />
            </>
          )}
        </span>
      </button>

      {open && (
        <div className="mt-4 border-t-2 border-ink pt-4 space-y-3">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {DISH_CATEGORIES.map((cat) => (
              <div
                key={cat.name}
                className="rounded-xl border-2 border-ink bg-sunken p-3 space-y-2"
              >
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className={`inline-block h-3 w-3 rounded-full border border-ink ${cat.color}`}
                  />
                  <span className="font-display text-xs font-bold uppercase tracking-wider text-muted">
                    {cat.name}
                  </span>
                </div>
                <ul className="flex flex-wrap gap-1.5">
                  {cat.dishes.map((dish) => (
                    <li
                      key={dish}
                      className="rounded-lg border-2 border-ink bg-surface px-2 py-0.5 text-xs font-bold text-ink shadow-brutal-none"
                    >
                      {dish}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <p className="rounded-lg border-2 border-ink bg-panel p-2.5 text-xs font-medium text-night">
            <strong>Unsure about a dish?</strong> Uploading meals outside these 25 will trigger the{' '}
            <span className="font-bold underline">Uncertain Triage</span> warning rather than guessing incorrectly.
          </p>
        </div>
      )}
    </div>
  );
}
