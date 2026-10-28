# Architecture & Implementation Decisions (`docs/DECISIONS.md`)

This document records design choices made where `PROJECT_SPEC.md` left implementation latitude or where platform-specific constraints arose.

## 1. Frontend Theme — Neo-Brutalism Reference Override
* **Context:** Section 7.0 of `PROJECT_SPEC.md` describes a slate dark theme, while the user explicitly provided a **Neo-Brutalism UI Component Library** reference sheet (`media_1793189592669_f8770ba7.png`).
* **Decision:** Implemented the Neo-Brutalist visual language from the user's attached reference image as the primary design system:
  * Warm cream canvas (`#FCEFE6`), crisp `2px–3px` ink borders (`#141414`), hard offset shadows (`4px 4px 0 0 #141414` and `6px 6px 0 0 #141414`) with tactile press translation on hover/active.
  * Self-hosted **Space Grotesk** (`@fontsource/space-grotesk`) for geometric bold display headers + **Inter** (`@fontsource/inter`) with `tabular-nums` for telemetry and macro numerals (100% offline, zero CDN requests).
  * Vibrant flat palette mapped to macronutrients: Protein (`#A78BFA` purple), Carbs (`#FFE066` yellow), Fat (`#F25F5C` coral), Fiber (`#3CCBB9` teal).
  * An optional Neo-Brutalist dark mode toggle (`useDarkMode`, persisted in `localStorage`) is included in the header.

## 2. Windows Path Ampersand (`&`) Hardening
* **Context:** The workspace directory (`Visual Meal Recognition & Macro Triage Engine`) contains an `&` character. On Windows, `cmd.exe` interprets unquoted `&` inside `node_modules\.bin\*.cmd` shims and `activate.bat` as a command separator (`'Macro' is not recognized...`).
* **Decision:**
  * In `frontend/package.json`, scripts invoke the CLI entrypoints via `node ./node_modules/...` relative paths (`tsc`, `vite`, `eslint`, `vitest`) so `npm run typecheck`, `npm run lint`, `npm run test`, and `npm run build` succeed regardless of special characters in parent directory names.
  * In `setup.bat`, `run_backend.bat`, `run_frontend.bat`, and `start.bat`, `VIRTUAL_ENV` and `PATH` are quoted (`set "VIRTUAL_ENV=%~dp0.venv"`) and `.venv\Scripts\python.exe` is invoked directly.

## 3. Single-Script Local Launcher (`start.bat` / `start.sh`)
* **Context:** In addition to `setup.{bat,sh}`, `run_backend.{bat,sh}`, and `run_frontend.{bat,sh}` from Section 12, the user requested that both components be launchable locally with a single script.
* **Decision:** Added `start.bat` (Windows) and `start.sh` (Linux/macOS) at the repository root. Running `start.bat` (or `./start.sh`) verifies the virtual environment and `node_modules`, starts the FastAPI backend on `http://127.0.0.1:8000` and the Vite React frontend on `http://127.0.0.1:5173`, and opens the browser. Furthermore, if `frontend/dist` is built (`npm run build`), FastAPI automatically mounts it at `/` for optional single-process serving.

## 4. Numerical Preprocessing Parity Contract
* **Context:** PIL and OpenCV bilinear/bicubic resize implementations differ subtly in antialiasing and pixel-center conventions, which is the most common source of notebook-vs-production drift.
* **Decision:** Standardized the evaluation transform (`Resize(shorter_side=256, cv2.INTER_LINEAR)` $\rightarrow$ `CenterCrop(224)` $\rightarrow$ `/255.0` $\rightarrow$ ImageNet normalize $\rightarrow$ `NCHW float32`) in both `notebooks/_shared/transforms.py::eval_numpy` and `backend/app/services/preprocessing.py::preprocess_rgb`. `backend/tests/test_preprocessing_parity.py` enforces `np.allclose(..., atol=1e-5)` across 5 fixture images.

## 5. OpenCV Headless & Albumentations Compatibility
* **Context:** `albumentations==1.4.21` depends on `albucore`, which works cleanly with `opencv-python-headless==4.10.0.84`.
* **Decision:** Kept `opencv-python-headless==4.10.0.84` across both `backend/requirements.txt` and `notebooks/requirements-notebooks.txt` so no GUI X11/Win32 libraries are required in headless environments.

## 6. Nutrition Registry Values
* **Context:** All 25 classes in `assets/nutrition_registry.json` were cross-checked against standard USDA FoodData Central per-serving approximations and Atwater energy consistency ($|4P + 4C + 9F - \text{kcal}| / \text{kcal} \le 0.12$).
* **Decision:** Retained the exact specification table values; all 25 entries satisfy the $\le 12\%$ Atwater calorie consistency check in `scripts/validate_artifacts.py`.

