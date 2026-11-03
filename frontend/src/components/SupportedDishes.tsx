import { useState } from 'react';
import { ChevronDown, ChevronUp, Utensils } from 'lucide-react';

interface DishCategory {
  name: string;
  color: string;
  dishes: string[];
}

export const DISH_CATEGORIES: DishCategory[] = [
  {
    name: 'Italian & Pasta',
    color: 'bg-coral',
    dishes: [
      'Pizza', 'Lasagna', 'Spaghetti Bolognese', 'Spaghetti Carbonara',
      'Ravioli', 'Gnocchi', 'Risotto', 'Bruschetta', 'Garlic Bread', 'Cannoli'
    ],
  },
  {
    name: 'Asian & Specialties',
    color: 'bg-sun',
    dishes: [
      'Chicken Curry', 'Ramen', 'Pad Thai', 'Fried Rice', 'Sushi',
      'Sashimi', 'Gyoza', 'Dumplings', 'Takoyaki', 'Bibimbap',
      'Peking Duck', 'Pho', 'Edamame', 'Miso Soup', 'Hot and Sour Soup', 'Spring Rolls'
    ],
  },
  {
    name: 'Meat, Steaks & Seafood',
    color: 'bg-tangerine',
    dishes: [
      'Steak', 'Filet Mignon', 'Prime Rib', 'Pork Chop', 'Baby Back Ribs',
      'Grilled Salmon', 'Fish and Chips', 'Crab Cakes', 'Lobster Bisque',
      'Lobster Roll Sandwich', 'Mussels', 'Oysters', 'Scallops', 'Fried Calamari',
      'Paella', 'Ceviche', 'Tuna Tartare', 'Beef Carpaccio', 'Beef Tartare', 'Escargots', 'Foie Gras'
    ],
  },
  {
    name: 'Fast Food, Sandwiches & Snacks',
    color: 'bg-coral',
    dishes: [
      'Hamburger', 'Hot Dog', 'French Fries', 'Onion Rings', 'Poutine',
      'Tacos', 'Chicken Quesadilla', 'Nachos', 'Samosa', 'Falafel',
      'Macaroni and Cheese', 'Club Sandwich', 'Grilled Cheese Sandwich',
      'Pulled Pork Sandwich', 'Croque Madame', 'Chicken Wings', 'Shrimp and Grits'
    ],
  },
  {
    name: 'Salads, Dips & Starters',
    color: 'bg-teal',
    dishes: [
      'Caesar Salad', 'Greek Salad', 'Caprese Salad', 'Beet Salad',
      'Seaweed Salad', 'Guacamole', 'Hummus', 'Cheese Plate',
      'Deviled Eggs', 'French Onion Soup', 'Clam Chowder'
    ],
  },
  {
    name: 'Breakfast & Brunch',
    color: 'bg-grape',
    dishes: [
      'Omelette', 'Eggs Benedict', 'Huevos Rancheros', 'Breakfast Burrito',
      'Pancakes', 'Waffles', 'French Toast'
    ],
  },
  {
    name: 'Desserts, Cakes & Pastries',
    color: 'bg-sun',
    dishes: [
      'Chocolate Cake', 'Cheesecake', 'Red Velvet Cake', 'Carrot Cake',
      'Apple Pie', 'Strawberry Shortcake', 'Tiramisu', 'Panna Cotta',
      'Creme Brulee', 'Chocolate Mousse', 'Baklava', 'Beignets',
      'Churros', 'Donuts', 'Cupcakes', 'Macarons', 'Bread Pudding',
      'Ice Cream', 'Frozen Yogurt'
    ],
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
              101 Supported Dishes
            </h3>
            <p className="text-xs text-muted sm:text-sm">
              CalorieCAM is tuned to recognize all 101 Food-101 culinary categories.
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
                    {cat.name} ({cat.dishes.length})
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
            <strong>Looking for another dish?</strong> If a meal outside these 101 is uploaded, CalorieCAM flags it with alternative suggestions rather than guessing blindly.
          </p>
        </div>
      )}
    </div>
  );
}

