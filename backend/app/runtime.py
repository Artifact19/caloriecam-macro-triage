"""Runtime container: loads artifacts at startup and hands out inference engines."""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol

import numpy as np

from .config import ENGINE_NAMES, Settings
from .services.nutrition import NutritionService
from .services.onnx_engine import OnnxEngine
from .services.torch_engine import TorchEngine

log = logging.getLogger("meal_triage.runtime")

ONNX_FILES = {
    "onnx_fp32": "mobilenetv3_food25_fp32.onnx",
    "onnx_int8_dynamic": "mobilenetv3_food25_int8_dynamic.onnx",
    "onnx_int8_static": "mobilenetv3_food25_int8_static.onnx",
}
CHECKPOINT = "mobilenetv3_food25.pt"
EXPECTED_FILES = ["class_names.json", CHECKPOINT, *ONNX_FILES.values(), "metrics.json", "benchmark.json"]
# Preference order when no explicit/benchmarked default is usable.
FALLBACK_ORDER = ("onnx_int8_static", "onnx_fp32", "onnx_int8_dynamic", "pytorch")


class Engine(Protocol):
    def predict_logits(self, batch: np.ndarray) -> np.ndarray: ...


def _read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@dataclass
class Runtime:
    settings: Settings
    started_at: float = field(default_factory=time.time)
    class_names: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    benchmark: dict[str, Any] = field(default_factory=dict)
    nutrition: Optional[NutritionService] = None
    torch_engine: Optional[TorchEngine] = None
    onnx_engines: dict[str, OnnxEngine] = field(default_factory=dict)
    default_engine: Optional[str] = None
    temperature: float = 1.0
    model_version: Optional[str] = None
    missing: list[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # ----------------------------------------------------------------- engines
    def available_engines(self) -> list[str]:
        """Engines whose artifact exists on disk (ONNX sessions may still be lazy)."""
        out = [n for n in ENGINE_NAMES if n != "pytorch" and (self.settings.models_dir / ONNX_FILES[n]).is_file()]
        if self.torch_engine is not None:
            out.append("pytorch")
        return out

    @property
    def ready(self) -> bool:
        return bool(self.class_names) and bool(self.available_engines())

    def get_engine(self, name: str) -> Engine:
        """Return a ready engine; ONNX sessions for non-default engines are created lazily."""
        if name == "pytorch":
            if self.torch_engine is None:
                raise KeyError(name)
            return self.torch_engine
        if name not in ONNX_FILES:
            raise KeyError(name)
        with self._lock:
            if name not in self.onnx_engines:
                path = self.settings.models_dir / ONNX_FILES[name]
                if not path.is_file():
                    raise KeyError(name)
                eng = OnnxEngine(path, self.settings.ort_intra_op_threads)
                eng.warmup()
                self.onnx_engines[name] = eng
            return self.onnx_engines[name]


def _resolve_default(settings: Settings, benchmark: dict[str, Any], available: list[str]) -> Optional[str]:
    for candidate in (settings.default_engine, benchmark.get("default_engine"), "onnx_fp32"):
        if candidate in available:
            return candidate
    for candidate in FALLBACK_ORDER:
        if candidate in available:
            return candidate
    return None


def build_runtime(settings: Settings) -> Runtime:
    """Load every artifact that exists. Never raises for *missing* files (the app still starts)."""
    rt = Runtime(settings=settings)
    models = settings.models_dir
    rt.missing = [f for f in EXPECTED_FILES if not (models / f).is_file()]

    registry = settings.assets_dir / "nutrition_registry.json"
    if registry.is_file():
        rt.nutrition = NutritionService(registry, settings.assets_dir, settings.usda_api_key)
    else:
        rt.missing.append("assets/nutrition_registry.json")

    names = _read_json(models / "class_names.json")
    rt.class_names = list(names) if isinstance(names, list) else []
    rt.metrics = _read_json(models / "metrics.json") or {}  # type: ignore[assignment]
    rt.benchmark = _read_json(models / "benchmark.json") or {}  # type: ignore[assignment]

    if rt.nutrition is not None and rt.class_names:
        rt.nutrition.validate_against(rt.class_names)  # RuntimeError with a clear message on mismatch

    ckpt = models / CHECKPOINT
    if ckpt.is_file() and rt.class_names:
        try:
            rt.torch_engine = TorchEngine(ckpt, rt.class_names)
        except Exception as exc:  # corrupt checkpoint -> degrade, report
            log.error("failed to load checkpoint: %s", exc)
            rt.missing.append(f"{CHECKPOINT} (unreadable: {exc})")

    temperature = (rt.torch_engine.temperature if rt.torch_engine else None) or rt.metrics.get("temperature")
    rt.temperature = float(temperature) if temperature else 1.0

    available = rt.available_engines()
    rt.default_engine = _resolve_default(settings, rt.benchmark, available)

    if rt.ready and rt.default_engine:
        # Eagerly create + warm the default ONNX engine; others are lazy.
        try:
            default = rt.get_engine(rt.default_engine)
            if isinstance(default, OnnxEngine):
                default.warmup()
        except Exception as exc:
            log.error("failed to load default engine %s: %s", rt.default_engine, exc)
        if rt.torch_engine is not None:
            rt.torch_engine.warmup()  # one classification + one Grad-CAM pass

        f1 = rt.metrics.get("val_macro_f1")
        if f1 is None and rt.torch_engine is not None:
            f1 = rt.torch_engine.metadata.get("val_macro_f1")
        arch = rt.torch_engine.arch if rt.torch_engine else "mobilenet_v3_large"
        rt.model_version = f"{arch.replace('_', '')}-food25-{float(f1):.4f}" if f1 is not None else f"{arch}-food25"
    log.info(
        "runtime ready=%s default_engine=%s engines=%s missing=%s",
        rt.ready,
        rt.default_engine,
        available,
        rt.missing,
    )
    return rt

