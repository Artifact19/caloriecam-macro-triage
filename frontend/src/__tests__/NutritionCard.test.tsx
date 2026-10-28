import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { NutritionCard } from '../components/NutritionCard';
import { scaleNutrition } from '../lib/format';
import type { Nutrition } from '../lib/types';

const pizza: Nutrition = {
  dish: 'pizza',
  display_name: 'Pizza',
  serving_description: '1 slice (107 g)',
  servings: 1,
  calories_kcal: 285,
  protein_g: 12,
  carbs_g: 36,
  fat_g: 10,
  fiber_g: 2.5,
  macro_energy_split: { protein_pct: 16.8, carbs_pct: 50.5, fat_pct: 32.7 },
  source: 'usda_approx',
};

describe('scaleNutrition', () => {
  it('scales numeric fields linearly and leaves the energy split unchanged', () => {
    const scaled = scaleNutrition(pizza, 2);
    expect(scaled.calories_kcal).toBe(570);
    expect(scaled.protein_g).toBe(24);
    expect(scaled.fiber_g).toBe(5);
    expect(scaled.servings).toBe(2);
    expect(scaled.macro_energy_split).toEqual(pizza.macro_energy_split);
  });

  it('is relative to the base servings of the response', () => {
    const base = { ...pizza, servings: 2, calories_kcal: 570 };
    expect(scaleNutrition(base, 1).calories_kcal).toBe(285);
  });
});

describe('NutritionCard', () => {
  it('shows per-serving values, the disclaimer and the serving description', () => {
    render(<NutritionCard nutrition={pizza} />);
    expect(screen.getByTestId('calories-total')).toHaveTextContent('285');
    expect(screen.getByText('Estimates are approximate and not medical advice.')).toBeInTheDocument();
    expect(screen.getByTestId('serving-description')).toHaveTextContent('1 slice (107 g)');
  });

  it('doubles every value when servings are set to 2\u00d7', () => {
    render(<NutritionCard nutrition={pizza} />);
    expect(within(screen.getByTestId('ring-protein')).getByText('12 g')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '2\u00d7' }));

    expect(screen.getByTestId('calories-total')).toHaveTextContent('570');
    expect(within(screen.getByTestId('ring-protein')).getByText('24 g')).toBeInTheDocument();
    expect(within(screen.getByTestId('ring-carbs')).getByText('72 g')).toBeInTheDocument();
    expect(within(screen.getByTestId('ring-fat')).getByText('20 g')).toBeInTheDocument();
    expect(screen.getByTestId('fiber-value')).toHaveTextContent('5 g');
  });

  it('supports a custom portion', () => {
    render(<NutritionCard nutrition={pizza} />);
    fireEvent.click(screen.getByRole('button', { name: 'Custom' }));
    fireEvent.change(screen.getByLabelText('Custom servings'), { target: { value: '3' } });
    expect(screen.getByTestId('calories-total')).toHaveTextContent('855');
  });

  it('marks alternatives', () => {
    render(<NutritionCard nutrition={pizza} viewingAlternative />);
    expect(screen.getByText('Viewing alternative')).toBeInTheDocument();
  });
});
