"""Generate ``assets/nutrition_registry.json`` and ``data/subset_classes.json``.

``ROWS`` holds approximate, USDA-style per-serving estimates for all 101 Food-101 dishes
(the classes the shipped model predicts). Re-run this script after editing ``ROWS`` to
regenerate both JSON files deterministically.

``data/subset_classes.json`` defines the model's output index order (Food-101's alphabetical
class order), so it is always written sorted, and the script refuses to write a class list
that differs from ``models/class_names.json`` (that would silently break the trained model).

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
    ("apple_pie", "1 slice", 125, 296, 2.4, 43, 14, 2),
    ("baby_back_ribs", "1 half rack", 250, 640, 48, 12, 44, 0),
    ("baklava", "1 piece", 50, 230, 3.5, 29, 12, 1.5),
    ("beef_carpaccio", "1 serving", 100, 145, 21, 1, 6.5, 0),
    ("beef_tartare", "1 serving", 150, 240, 30, 2, 12, 0.5),
    ("beet_salad", "1 bowl", 180, 150, 3.5, 16, 8, 4),
    ("beignets", "3 pieces", 110, 380, 6, 54, 16, 1.5),
    ("bibimbap", "1 bowl", 400, 560, 24, 82, 16, 6),
    ("bread_pudding", "1 slice", 150, 310, 7, 48, 11, 1.2),
    ("breakfast_burrito", "1 burrito", 200, 420, 18, 38, 22, 3),
    ("bruschetta", "2 pieces", 90, 170, 4.5, 24, 6.5, 1.8),
    ("cannoli", "1 large", 100, 280, 6, 32, 14, 1),
    ("caprese_salad", "1 plate", 200, 280, 14, 6, 22, 1.5),
    ("carrot_cake", "1 slice", 120, 415, 4.5, 55, 21, 2),
    ("ceviche", "1 cup", 180, 175, 24, 9, 4, 1.5),
    ("cheese_plate", "1 assorted board", 120, 460, 28, 4, 38, 0.5),
    ("cheesecake", "1 slice", 125, 400, 7, 32, 28, 0.8),
    ("chicken_quesadilla", "1 quesadilla", 180, 490, 28, 38, 26, 2.5),
    ("chicken_wings", "6 wings", 180, 430, 34, 4, 31, 0.2),
    ("chocolate_mousse", "1 ramekin", 100, 275, 4.5, 26, 18, 2),
    ("churros", "3 pieces", 100, 360, 4, 42, 20, 1.5),
    ("clam_chowder", "1 bowl", 240, 210, 9, 20, 10, 1.5),
    ("club_sandwich", "1 whole", 250, 580, 32, 46, 29, 3.5),
    ("crab_cakes", "2 cakes", 140, 290, 22, 12, 17, 0.8),
    ("creme_brulee", "1 dish", 130, 390, 5, 32, 28, 0.2),
    ("croque_madame", "1 sandwich", 220, 540, 26, 36, 32, 2),
    ("cup_cakes", "1 cupcake", 75, 260, 2.5, 38, 12, 0.5),
    ("deviled_eggs", "4 halves", 120, 220, 12, 2, 18, 0.2),
    ("dumplings", "6 pieces", 180, 340, 14, 42, 12, 2.2),
    ("edamame", "1 cup in pods", 150, 190, 17, 14, 8, 8),
    ("eggs_benedict", "1 serving", 220, 560, 24, 28, 40, 1.2),
    ("escargots", "6 escargots", 100, 210, 16, 3, 15, 0),
    ("falafel", "4 patties", 120, 330, 13, 32, 18, 6.5),
    ("filet_mignon", "1 steak, cooked", 170, 350, 44, 0, 19, 0),
    ("fish_and_chips", "1 fillet with fries", 300, 680, 28, 68, 34, 4.5),
    ("foie_gras", "1 slice", 60, 280, 7, 2.8, 27, 0),
    ("french_onion_soup", "1 bowl with cheese", 250, 290, 13, 22, 17, 2),
    ("french_toast", "2 slices", 140, 310, 10, 44, 11, 2),
    ("fried_calamari", "1 plate", 150, 380, 22, 28, 20, 1.2),
    ("frozen_yogurt", "1 cup", 150, 220, 5.5, 38, 5, 0),
    ("garlic_bread", "2 slices", 80, 280, 6, 32, 14, 1.8),
    ("gnocchi", "1 bowl", 200, 320, 7, 62, 4.5, 3.5),
    ("grilled_cheese_sandwich", "1 sandwich", 130, 390, 14, 30, 24, 1.8),
    ("gyoza", "6 pieces", 150, 280, 12, 32, 11, 1.8),
    ("hot_and_sour_soup", "1 bowl", 240, 120, 6, 14, 4.5, 1.5),
    ("huevos_rancheros", "1 plate", 250, 460, 18, 42, 25, 6),
    ("lobster_bisque", "1 bowl", 240, 260, 11, 16, 17, 0.8),
    ("lobster_roll_sandwich", "1 roll", 200, 440, 24, 36, 22, 1.5),
    ("macaroni_and_cheese", "1 cup", 200, 380, 14, 42, 18, 2),
    ("macarons", "3 macarons", 60, 250, 4, 34, 11, 1.2),
    ("miso_soup", "1 bowl", 200, 45, 3, 5, 1.5, 1),
    ("mussels", "1 bowl in broth", 250, 210, 24, 8, 8.5, 0),
    ("nachos", "1 plate with cheese", 200, 580, 16, 56, 34, 5),
    ("onion_rings", "8 rings", 120, 340, 4, 38, 19, 2.5),
    ("oysters", "6 raw oysters", 100, 68, 7, 4, 2.5, 0),
    ("paella", "1 plate", 300, 480, 26, 62, 14, 3.5),
    ("panna_cotta", "1 serving", 120, 290, 4, 26, 19, 0.2),
    ("peking_duck", "3 rolls with duck", 180, 460, 24, 32, 26, 1.8),
    ("pho", "1 large bowl", 450, 410, 26, 60, 6.5, 3),
    ("pork_chop", "1 bone-in, cooked", 180, 390, 46, 0, 22, 0),
    ("poutine", "1 container", 250, 620, 16, 66, 32, 4),
    ("prime_rib", "1 cut, cooked", 220, 580, 48, 0, 42, 0),
    ("pulled_pork_sandwich", "1 sandwich", 220, 520, 32, 48, 22, 2.2),
    ("ravioli", "1 bowl in sauce", 220, 360, 15, 48, 12, 3),
    ("red_velvet_cake", "1 slice", 130, 430, 4.5, 58, 21, 1.5),
    ("risotto", "1 bowl", 240, 380, 8, 54, 14, 1.8),
    ("sashimi", "8 pieces assorted", 140, 180, 32, 0, 5, 0),
    ("scallops", "6 seared scallops", 150, 165, 25, 5, 4.5, 0),
    ("seaweed_salad", "1 bowl", 120, 95, 2, 12, 4.5, 3),
    ("shrimp_and_grits", "1 bowl", 280, 440, 26, 44, 18, 2),
    ("spaghetti_carbonara", "1 bowl", 250, 520, 22, 58, 22, 2.5),
    ("spring_rolls", "2 fried rolls", 120, 260, 6, 32, 12, 2),
    ("strawberry_shortcake", "1 serving", 150, 360, 5, 48, 17, 2.5),
    ("takoyaki", "6 balls", 160, 310, 11, 38, 12, 1.8),
    ("tiramisu", "1 slice", 120, 340, 6, 36, 19, 1),
    ("tuna_tartare", "1 plate", 150, 195, 28, 3, 7.5, 0.8),
]

DISPLAY_OVERRIDES = {
    "cup_cakes": "Cupcakes",
    "fish_and_chips": "Fish and Chips",
    "hot_and_sour_soup": "Hot and Sour Soup",
    "macaroni_and_cheese": "Macaroni and Cheese",
    "shrimp_and_grits": "Shrimp and Grits",
}


def _num(x: float) -> float | int:
    """Render whole floats as ints so the JSON stays tidy."""
    return int(x) if float(x).is_integer() else x


def build_registry() -> dict:
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
    return {
        "version": "1.0",
        "disclaimer": (
            "Approximate values per standard serving; typical USDA-style estimates, "
            "±15%. Not medical advice."
        ),
        "items": items,
    }


def build_classes() -> list[str]:
    names = [r[0] for r in ROWS]
    if len(set(names)) != len(names):
        raise SystemExit("ROWS contains duplicate dish names")
    return sorted(names)


def build() -> None:
    registry = build_registry()
    classes = build_classes()
    trained = ROOT / "models" / "class_names.json"
    if trained.is_file():
        model_classes = json.loads(trained.read_text(encoding="utf-8"))
        if model_classes != classes:
            raise SystemExit(
                "Refusing to write: the class list from ROWS differs from models/class_names.json "
                f"(missing={sorted(set(model_classes) - set(classes))}, "
                f"extra={sorted(set(classes) - set(model_classes))}). Retrain the model first."
            )
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "assets" / "nutrition_registry.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (ROOT / "data" / "subset_classes.json").write_text(json.dumps(classes, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(registry['items'])} registry items and subset_classes.json")


if __name__ == "__main__":
    build()
