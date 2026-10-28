"""Pydantic request/response models (mirrored by ``frontend/src/lib/types.ts``)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

TriageLevel = Literal["confident", "review", "uncertain"]


class ErrorResponse(BaseModel):
    detail: str
    code: str


class Prediction(BaseModel):
    label: str
    display_name: str
    confidence: float = Field(ge=0, le=1)


class MacroEnergySplit(BaseModel):
    """Percent of calories from each macro (4/4/9 kcal per g), normalised to 100."""

    protein_pct: float
    carbs_pct: float
    fat_pct: float


class NutritionInfo(BaseModel):
    dish: str
    display_name: str
    serving_description: str
    servings: float
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    macro_energy_split: MacroEnergySplit
    source: str


class NutritionList(BaseModel):
    disclaimer: str
    items: list[NutritionInfo]


class Alternative(Prediction):
    """A runner-up class with its per-serving nutrition (for triage)."""

    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    serving_description: str


class Triage(BaseModel):
    level: TriageLevel
    message: str
    alternatives_with_nutrition: list[Alternative] = Field(default_factory=list)


class GradcamResult(BaseModel):
    target_class: str
    heatmap_png_base64: str
    overlay_png_base64: str
    width: int
    height: int


class Latency(BaseModel):
    preprocess_ms: float
    inference_ms: float
    gradcam_ms: float
    postprocess_ms: float
    total_ms: float
    classification_path_ms: float


class ImageInfo(BaseModel):
    original_width: int
    original_height: int


class PredictResponse(BaseModel):
    top1: Prediction
    topk: list[Prediction]
    triage: Triage
    nutrition: NutritionInfo
    gradcam: Optional[GradcamResult] = None
    latency: Latency
    engine: str
    model_version: str
    image: ImageInfo


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    engines: list[str]
    default_engine: Optional[str]
    num_classes: int
    classes: list[str]
    model_version: Optional[str]
    onnxruntime_version: str
    torch_version: str
    uptime_s: float
    missing_artifacts: list[str]

