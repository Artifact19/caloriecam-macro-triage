"""``GET /nutrition`` and ``GET /nutrition/{dish_name}`` (also under ``/api``)."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from ..errors import AppError
from ..runtime import Runtime
from ..schemas import NutritionInfo, NutritionList
from ..services.nutrition import MAX_SERVINGS, MIN_SERVINGS, NutritionService

router = APIRouter(tags=["nutrition"])


def _service(request: Request) -> NutritionService:
    rt: Runtime = request.app.state.runtime
    if rt.nutrition is None:
        raise AppError(503, "Nutrition registry not found.", "registry_missing")
    return rt.nutrition


@router.get("/nutrition", response_model=NutritionList, summary="List all 25 dishes in the nutrition registry")
def list_nutrition(request: Request) -> NutritionList:
    svc = _service(request)
    return NutritionList(disclaimer=svc.disclaimer, items=svc.list_all())


@router.get(
    "/nutrition/{dish_name}",
    response_model=NutritionInfo,
    summary="Per-serving nutrition for a dish (scaled by servings)",
)
def get_nutrition(
    dish_name: str,
    request: Request,
    servings: float = Query(1.0, ge=MIN_SERVINGS, le=MAX_SERVINGS, description="Number of servings (0.25-10)"),
) -> NutritionInfo:
    return _service(request).get_nutrition(dish_name, servings=servings)

