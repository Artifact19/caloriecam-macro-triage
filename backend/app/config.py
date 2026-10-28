"""Runtime configuration (pydantic-settings; reads the repo-root ``.env`` if present)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: ``<repo>/backend/app/config.py`` -> repo root.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]

ENGINE_NAMES = ("onnx_int8_static", "onnx_int8_dynamic", "onnx_fp32", "pytorch")


class Settings(BaseSettings):
    """Environment-driven settings. Every field maps to an upper-case env var of the same name."""

    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    models_dir: Path = REPO_ROOT / "models"
    assets_dir: Path = REPO_ROOT / "assets"
    default_engine: Optional[str] = None
    conf_threshold_high: float = 0.70
    conf_threshold_low: float = 0.40
    max_upload_mb: float = 10
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    usda_api_key: Optional[str] = None
    ort_intra_op_threads: int = 0

    @field_validator("models_dir", "assets_dir", mode="after")
    @classmethod
    def _absolute(cls, v: Path) -> Path:
        """Relative paths in ``.env`` are interpreted relative to the repo root."""
        return v if v.is_absolute() else (REPO_ROOT / v).resolve()

    @field_validator("usda_api_key", "default_engine", mode="before")
    @classmethod
    def _blank_to_none(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("default_engine")
    @classmethod
    def _valid_engine(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ENGINE_NAMES:
            raise ValueError(f"DEFAULT_ENGINE must be one of {ENGINE_NAMES}")
        return v

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @property
    def frontend_dist(self) -> Path:
        return REPO_ROOT / "frontend" / "dist"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

