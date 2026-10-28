"""Generate ``assets/nutrition_registry.json`` and ``data/subset_classes.json``.

The values come straight from PROJECT_SPEC.md section 4.1 (approximate, USDA-style
per-serving estimates). Re-run this script after editing ``ROWS`` to regenerate
both JSON files deterministically.

Usage:  python scripts/build_registry.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# class, serving description, grams, kcal, protein, carbs, fat, fiber
ROWS: list[tuple[str, str, float, float, float, float, float, float]] = [
    ("pizza", "1 slice", 107, 285, 12, 36, 10, 2.5),
    ("caesar_salad", "1 bowl", 200, 310, 8, 12, 26, 2),
    ("greek_salad", "1 bowl", 250, 230, 6, 12, 18, 3),
    ("steak", "1 sirloin, cooked", 170, 330, 46, 0, 15, 0),
    ("chicken_curry", "1 cup", 250, 330, 24, 12, 20, 3),
    ("hamburger", "1 burger", 220, 540, 28, 42, 28, 2),
    ("french_fries", "1 medium", 117, 365, 4, 48, 17, 4),
    ("sushi", "6 pieces", 180, 260, 9, 48, 4, 2),
    ("ramen", "1 bowl", 450, 450, 18, 60, 16, 3),
    ("spaghetti_bolognese", "1 plate", 350, 570, 28, 70, 20, 6),
    ("tacos", "2 tacos", 170, 340, 16, 28, 18, 4),
    ("fried_rice", "1 cup", 200, 330, 8, 50, 11, 2),
    ("pancakes", "3 pancakes", 150, 330, 9, 50, 11, 2),
    ("waffles", "2 waffles", 150, 430, 10, 54, 20, 2),
    ("ice_cream", "1 cup", 132, 270, 5, 31, 14, 1),
    ("chocolate_cake", "1 slice", 100, 380, 5, 50, 18, 3),
    ("omelette", "3-egg", 180, 300, 20, 3, 23, 0),
    ("guacamole", "\u00bd cup", 120, 200, 2, 10, 17, 7),
    ("hot_dog", "1 with bun", 150, 300, 11, 24, 18, 1),
    ("lasagna", "1 piece", 300, 490, 28, 45, 22, 4),
    ("samosa", "2 pieces", 120, 300, 5, 32, 17, 3),
    ("hummus", "\u00bd cup", 120, 210, 6, 17, 13, 6),
    ("pad_thai", "1 plate", 300, 560, 20, 70, 22, 4),
    ("donuts", "1 glazed", 60, 260, 3, 30, 14, 1),
    ("grilled_salmon", "1 fillet", 150, 310, 34, 0, 19, 0),
]

DISPLAY_OVERRIDES = {"hot_dog": "Hot Dog", "pad_thai": "Pad Thai"}


def _num(x: float) -> float | int:
    """Render whole floats as ints so the JSON stays tidy."""
    return int(x) if float(x).is_integer() else x


def build() -> None:
    items: dict[str, dict] = {}
    for name, serving, grams, kcal, p, c, f, fib in ROWS:
        g = _num(grams)
        items[name] = {
            "display_name": DISPLAY_OVERRIDES.get(name, name.replace("_", " ").title()),
            "serving_description": f"{serving} ({g} g)",
            "serving_grams": g,
            "calories_kcal": _num(kcal),
            "protein_g": _num(p),
            "carbs_g": _num(c),
            "fat_g": _num(f),
            "fiber_g": _num(fib),
            "source": "usda_approx",
        }
    registry = {
        "version": "1.0",
        "disclaimer": (
            "Approximate values per standard serving; typical USDA-style estimates, "
            "\u00b115%. Not medical advice."
        ),
        "items": items,
    }
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "assets" / "nutrition_registry.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (ROOT / "data" / "subset_classes.json").write_text(
        json.dumps([r[0] for r in ROWS], indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(items)} registry items and subset_classes.json")


if __name__ == "__main__":
    build()

