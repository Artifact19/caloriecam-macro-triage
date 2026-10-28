"""Resolve repository-relative locations so notebooks run from any cwd.

Set ``MEAL_TRIAGE_DATA_DIR`` / ``MEAL_TRIAGE_MODELS_DIR`` to redirect inputs and outputs
(for example during an isolated smoke test).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

#: Repository root (``notebooks/_shared/paths.py`` -> parents[2]).
ROOT: Path = Path(__file__).resolve().parents[2]
MODELS: Path = Path(os.environ.get("MEAL_TRIAGE_MODELS_DIR", str(ROOT / "models"))).resolve()
DATA: Path = Path(os.environ.get("MEAL_TRIAGE_DATA_DIR", str(ROOT / "data"))).resolve()
ASSETS: Path = ROOT / "assets"
NOTEBOOKS: Path = ROOT / "notebooks"
RAW: Path = Path(os.environ.get("MEAL_TRIAGE_RAW_DIR", str(DATA / "raw"))).resolve()

for _d in (MODELS, DATA):
    _d.mkdir(parents=True, exist_ok=True)

# Make ``import _shared...`` work even if the kernel cwd is not notebooks/.
if str(NOTEBOOKS) not in sys.path:
    sys.path.insert(0, str(NOTEBOOKS))
