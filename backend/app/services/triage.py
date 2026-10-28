"""Confidence policy: map the top-1 probability to a triage level."""
from __future__ import annotations

from typing import Callable

from ..schemas import Alternative, NutritionInfo, Prediction, Triage

MESSAGES = {
    "confident": "High confidence prediction.",
    "review": "Moderately confident. Check the alternatives below.",
    "uncertain": "Low confidence. The dish may not be among the 25 supported classes.",
}


def triage_level(confidence: float, high: float, low: float) -> str:
    """``>= high`` confident; ``[low, high)`` review; ``< low`` uncertain."""
    if confidence >= high:
        return "confident"
    if confidence >= low:
        return "review"
    return "uncertain"


def build_triage(
    confidence: float,
    topk: list[Prediction],
    nutrition_for: Callable[[str], NutritionInfo],
    high: float,
    low: float,
    n_alternatives: int = 3,
) -> Triage:
    """Create the ``Triage`` object; non-confident levels carry the top-3 with nutrition."""
    level = triage_level(confidence, high, low)
    alternatives: list[Alternative] = []
    if level != "confident":
        for p in topk[:n_alternatives]:
            n = nutrition_for(p.label)
            alternatives.append(
                Alternative(
                    label=p.label,
                    display_name=p.display_name,
                    confidence=p.confidence,
                    calories_kcal=n.calories_kcal,
                    protein_g=n.protein_g,
                    carbs_g=n.carbs_g,
                    fat_g=n.fat_g,
                    fiber_g=n.fiber_g,
                    serving_description=n.serving_description,
                )
            )
    return Triage(level=level, message=MESSAGES[level], alternatives_with_nutrition=alternatives)  # type: ignore[arg-type]
