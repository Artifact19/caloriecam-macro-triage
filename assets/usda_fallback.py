"""Optional online fallback: USDA FoodData Central search (disabled unless USDA_API_KEY is set).

Used only by ``GET /nutrition/{dish_name}`` for dishes that are NOT in the local registry.
Nothing else depends on it. 3 s timeout; any failure returns ``None`` (the API turns that into a
friendly 404). Results are cached in memory (LRU 256). The key is sent in the ``X-Api-Key``
header so it never appears in URLs or logs.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Optional

import httpx

FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
TIMEOUT_S = 3.0

# FoodData Central nutrient numbers
_ENERGY_KCAL = ("208", "957", "958")  # 957/958 = Atwater energy, used by Foundation foods
_PROTEIN = ("203",)
_CARBS = ("205",)
_FAT = ("204",)
_FIBER = ("291",)


def _pick(nutrients: dict[str, float], numbers: tuple[str, ...]) -> float:
    for n in numbers:
        if n in nutrients:
            return float(nutrients[n])
    return 0.0


def parse_search_response(payload: dict[str, Any], query: str) -> Optional[dict[str, Any]]:
    """Extract per-100 g macros from the first Foundation / SR Legacy hit (or None)."""
    foods = payload.get("foods") or []
    preferred = [f for f in foods if f.get("dataType") in ("Foundation", "SR Legacy")]
    food = (preferred or foods or [None])[0]
    if not food:
        return None
    nutrients: dict[str, float] = {}
    for fn in food.get("foodNutrients", []):
        number = str(fn.get("nutrientNumber") or fn.get("number") or "")
        value = fn.get("value", fn.get("amount"))
        if number and value is not None:
            nutrients[number] = float(value)
    kcal = _pick(nutrients, _ENERGY_KCAL)
    if kcal <= 0 and not nutrients:
        return None
    return {
        "display_name": (food.get("description") or query).title(),
        "serving_description": "100 g",
        "serving_grams": 100,
        "calories_kcal": kcal,
        "protein_g": _pick(nutrients, _PROTEIN),
        "carbs_g": _pick(nutrients, _CARBS),
        "fat_g": _pick(nutrients, _FAT),
        "fiber_g": _pick(nutrients, _FIBER),
        "source": "usda_fdc_live",
    }


@lru_cache(maxsize=256)
def _cached_lookup(query: str, api_key: str) -> Optional[tuple[tuple[str, Any], ...]]:
    # Exceptions propagate on purpose: ``lru_cache`` never caches them, so a transient
    # network failure is retried on the next request instead of sticking.
    resp = httpx.get(
        FDC_SEARCH_URL,
        params={"query": query, "dataType": "Foundation,SR Legacy", "pageSize": 5},
        headers={"X-Api-Key": api_key},
        timeout=TIMEOUT_S,
    )
    resp.raise_for_status()
    parsed = parse_search_response(resp.json(), query)
    return tuple(parsed.items()) if parsed else None


def lookup(query: str, api_key: Optional[str]) -> Optional[dict[str, Any]]:
    """Return a 100 g nutrition dict for ``query`` or ``None``. No-op without an API key."""
    if not api_key or not query.strip():
        return None
    try:
        cached = _cached_lookup(query.strip().lower(), api_key)
    except Exception:  # network, HTTP status, JSON: all map to "not found"
        return None
    return dict(cached) if cached else None


def clear_cache() -> None:
    _cached_lookup.cache_clear()
