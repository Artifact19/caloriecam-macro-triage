"""Nutrition registry loader, normalisation, scaling and optional USDA fallback."""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

from ..errors import AppError
from ..schemas import MacroEnergySplit, NutritionInfo

MIN_SERVINGS = 0.25
MAX_SERVINGS = 10.0
KCAL_PER_G = {"protein": 4.0, "carbs": 4.0, "fat": 9.0}
_NUMERIC_FIELDS = ("calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g")


def normalize_dish_name(name: str) -> str:
    """``'Chicken Curry'``, ``'chicken-curry'`` and ``'chicken_curry'`` -> ``'chicken_curry'``."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def energy_split(protein_g: float, carbs_g: float, fat_g: float) -> MacroEnergySplit:
    """Percent of calories from P/C/F using 4/4/9 kcal per gram, normalised to 100."""
    kp, kc, kf = protein_g * KCAL_PER_G["protein"], carbs_g * KCAL_PER_G["carbs"], fat_g * KCAL_PER_G["fat"]
    total = kp + kc + kf
    if total <= 0:
        return MacroEnergySplit(protein_pct=0.0, carbs_pct=0.0, fat_pct=0.0)
    return MacroEnergySplit(
        protein_pct=round(100 * kp / total, 1),
        carbs_pct=round(100 * kc / total, 1),
        fat_pct=round(100 * kf / total, 1),
    )


def _load_fallback(assets_dir: Path) -> Optional[ModuleType]:
    path = assets_dir / "usda_fallback.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("usda_fallback", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NutritionService:
    """Loads ``nutrition_registry.json`` once; all lookups are in-memory."""

    def __init__(self, registry_path: Path, assets_dir: Optional[Path] = None, usda_api_key: Optional[str] = None) -> None:
        data = json.loads(Path(registry_path).read_text(encoding="utf-8"))
        self.items: dict[str, dict[str, Any]] = data["items"]
        self.disclaimer: str = data.get("disclaimer", "")
        self.version: str = data.get("version", "")
        self._usda_key = usda_api_key
        self._fallback = _load_fallback(assets_dir or Path(registry_path).parent) if usda_api_key else None

    # ------------------------------------------------------------------ registry
    @property
    def dishes(self) -> list[str]:
        return list(self.items)

    def validate_against(self, class_names: list[str]) -> None:
        """Startup check: registry keys must equal ``class_names.json`` exactly."""
        reg, cls = set(self.items), set(class_names)
        if reg != cls:
            raise RuntimeError(
                "nutrition_registry.json keys do not match class_names.json. "
                f"Missing from registry: {sorted(cls - reg)}; extra in registry: {sorted(reg - cls)}."
            )

    def display_name(self, label: str) -> str:
        item = self.items.get(label)
        return item["display_name"] if item else label.replace("_", " ").title()

    # ------------------------------------------------------------------ lookup
    @staticmethod
    def _check_servings(servings: float) -> float:
        if not (MIN_SERVINGS <= servings <= MAX_SERVINGS):
            raise AppError(
                422,
                f"servings must be between {MIN_SERVINGS:g} and {MAX_SERVINGS:g}.",
                "invalid_servings",
            )
        return float(servings)

    def _scale(self, dish: str, item: dict[str, Any], servings: float) -> NutritionInfo:
        scaled = {f: round(float(item[f]) * servings, 2) for f in _NUMERIC_FIELDS}
        return NutritionInfo(
            dish=dish,
            display_name=item["display_name"],
            serving_description=item["serving_description"],
            servings=servings,
            macro_energy_split=energy_split(scaled["protein_g"], scaled["carbs_g"], scaled["fat_g"]),
            source=item.get("source", "usda_approx"),
            **scaled,
        )

    def get_nutrition(self, dish: str, servings: float = 1.0) -> NutritionInfo:
        """Scaled nutrition for a registry dish (or the USDA fallback if configured).

        Raises ``AppError(404)`` for unknown dishes and ``AppError(422)`` for bad servings.
        """
        servings = self._check_servings(servings)
        key = normalize_dish_name(dish)
        item = self.items.get(key)
        if item is not None:
            return self._scale(key, item, servings)
        if self._fallback is not None and self._usda_key:
            live = self._fallback.lookup(dish, self._usda_key)
            if live:
                return self._scale(key, live, servings)
        raise AppError(404, f"Unknown dish '{dish}'. Known: {self.dishes}", "unknown_dish")

    def list_all(self) -> list[NutritionInfo]:
        return [self._scale(k, v, 1.0) for k, v in self.items.items()]

