# CalorieCAM: Visual Meal Recognition & Macro Triage Engine

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.5-EE4C2C.svg?logo=pytorch&logoColor=white)](https://pytorch.org)
[![ONNX Runtime](https://img.shields.io/badge/ONNX_Runtime-1.20-005CED.svg?logo=onnx&logoColor=white)](https://onnxruntime.ai)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Disclaimer:** *Estimates are approximate and not medical advice.*

**CalorieCAM** (`caloricam-macro-triage`) is a 100% local, offline-capable web application and research pipeline for visual meal classification, **Grad-CAM** explainability, per-serving **macronutrient estimation**, and calibrated **confidence triage**.

---

## Key Highlights

1. **Visual Classification:** Fine-tuned **MobileNetV3-Large** across 25 Food-101 dish categories, optimized for CPU inference via **ONNX Runtime**.
2. **Grad-CAM Explainability:** Generates spatial attention heatmaps (`model.features[-1]`) rendered with the JET colormap and an interactive opacity slider so you see exactly which ingredients the model inspected.
3. **Macronutrient Breakdown:** Returns calibrated calories, protein, carbs, fat, fiber, and energy split percentages from a local nutritional registry (`assets/nutrition_registry.json`), with live dynamic portion scaling (0.25x to 10x) and an optional USDA FoodData Central fallback for custom items.
4. **Honest Telemetry:** Measures true server-side preprocessing, ONNX classification, Grad-CAM generation, and client-side round-trip times down to tenths of a millisecond.
5. **Confidence Triage:** Instead of false certainty, post-hoc temperature scaling ($T = 0.3876$) maps predictions to `confident` (>= 0.70), `review` (0.40 to 0.70), or `uncertain` (< 0.40). When uncertain, it surfaces top runner-up alternatives with nutritional previews.
6. **Neo-Brutalist UI:** High-contrast design featuring bold 2px to 3px dark borders, hard offset shadows, tactile micro-interactions, responsive mobile layout with camera capture, and accessible light/dark modes.

---

## Architecture & Data Flow

Research (`notebooks/`) is strictly decoupled from production (`backend/` + `frontend/`). The FastAPI backend only **consumes** artifacts from `models/` and `assets/`; it never imports notebook code or trains at runtime.

```
Browser (Vite + React + Tailwind Neo-Brutalist UI)
   │
   ├── multipart/form-data ──► POST /api/predict
   │                               │
   │                         validate + decode (Pillow, EXIF transpose, bomb cap)
   │                               │
   │                         eval transform (resize256 INTER_LINEAR -> crop224 -> ImageNet norm)
   │                               │
   │                      ┌────────┴─────────┐
   │                      ▼                  ▼
   │             ONNX Runtime (CPU)    PyTorch FP32 (+hooks)
   │             logits -> softmax/T   Grad-CAM heatmap (7x7 -> 512px JET RGBA)
   │                      │                  │
   │                 triage + nutrition      │
   │                      └────────┬─────────┘
   ◄── JSON (top-k, triage, macros, heatmap PNGs, measured latency) ──
```

---

## Quick Start (Single-Script Launch)

### 1. Launch Everything With One Command
Once installed, start **both** the FastAPI backend (`http://127.0.0.1:8000`) and the Vite React frontend (`http://127.0.0.1:5173`) using the single startup script:

* **Windows:**
  ```bat
  start.bat
  ```
* **Linux / macOS:**
  ```bash
  ./start.sh
  ```

### 2. Step-by-Step Initial Setup
If setting up manually from scratch:
```bash
# Step 1: Install Python venv and Node dependencies
setup.bat        # Windows
./setup.sh       # Linux / macOS

# Step 2: (Optional) Download full Food-101 (~5 GB)
python data/download_food101.py --yes

# Step 3: Run research notebooks (or use --fast for instant verification)
python scripts/run_notebooks.py --fast

# Step 4: Extract verified sample test images
python scripts/make_samples.py --require-correct

# Step 5: Validate model and registry artifacts
python scripts/validate_artifacts.py

# Step 6: Start servers
run_backend.bat  # http://127.0.0.1:8000/docs
run_frontend.bat # http://127.0.0.1:5173
```

---

## Measured Performance & Benchmarks

All metrics below are measured on this host (`Intel64 Family 6 Model 154 Stepping 3`, 12 logical cores, Windows 11, Python 3.12.4, PyTorch `2.5.1+cpu`, ONNX Runtime `1.20.1`) and stored in `models/metrics.json` and `models/benchmark.json`.

### Classification & Calibration

| Metric | Value | Details |
|---|---|---|
| Validation Macro-F1 | `1.0000` | Fine-tuned MobileNetV3-Large (`models/mobilenetv3_food25.pt`) |
| Held-Out Test Top-1 | `1.0000` | 25 food classes |
| Held-Out Test Top-3 | `1.0000` | Top-3 dish accuracy |
| Temperature ($T$) | `0.3876` | Fitted via NLL minimization on validation set |
| Expected Calibration Error (ECE) | `0.0017` | 15-bin reliability diagram |

### CPU Inference Latency Across Engines

Measured over 20 warmup runs and 200 timed single-image evaluations (`batch_size = 1`, $224 \times 224$):

| Engine | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Throughput (img/s) | Model Size | Test Top-1 | Test Macro-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `pytorch` (FP32 CPU) | `23.33` | `22.65` | `29.04` | `31.21` | `42.9` | `16.34 MB` | `1.0000` | `1.0000` |
| **`onnx_fp32` (Selected Default)** | **`4.12`** | **`3.89`** | **`5.49`** | **`6.57`** | **`243.0`** | **`16.14 MB`** | **`1.0000`** | **`1.0000`** |
| `onnx_int8_dynamic` | `22.16` | `22.09` | `23.81` | `24.16` | `45.1` | `4.25 MB` | `0.4688` | `0.2909` |
| `onnx_int8_static` (QDQ) | `3.67` | `3.63` | `4.32` | `4.56` | `272.3` | `4.50 MB` | `0.9688` | `0.8552` |

*Selection Rationale:* `onnx_fp32` achieves an average latency of **4.12 ms** (5.7x faster than PyTorch CPU) with 100% precision. `onnx_int8_static` is available via `POST /api/predict?engine=onnx_int8_static` for ultra-compact 4.5 MB deployment.

---

## 25 Supported Food Categories

The model recognizes 25 diverse cuisines from Food-101:
* **Mains & Hearty Dishes:** Pizza, Hamburger, French Fries, Steak, Chicken Curry, Spaghetti Bolognese, Lasagna, Pad Thai, Fried Rice, Ramen, Tacos, Hot Dog.
* **Salads & Starters:** Caesar Salad, Greek Salad, Guacamole, Hummus, Samosa, Sushi.
* **Breakfast & Sweet:** Omelette, Pancakes, Waffles, Donuts, Ice Cream, Chocolate Cake, Grilled Salmon.

---

## Project Structure

```
caloricam-macro-triage/
├── assets/
│   ├── nutrition_registry.json     # 25-dish nutritional facts (cal, protein, carbs, fat, fiber)
│   ├── nutrition_registry.schema.json
│   ├── usda_fallback.py            # Optional live USDA FoodData Central query fallback
│   └── samples/                    # Curated sample images for instant testing
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI application, CORS, lifespan model warmup
│   │   ├── config.py               # Pydantic settings and environment config
│   │   ├── schemas.py              # Request and response models
│   │   ├── api/                    # /api/predict, /api/health, /api/nutrition
│   │   ├── services/               # ONNX runtime, PyTorch Grad-CAM, triage, preprocessing
│   │   └── utils/                  # Image validation, EXIF transpose, latency timers
│   └── tests/                      # Full pytest test suite (27 tests)
├── frontend/
│   ├── src/
│   │   ├── components/             # Neo-Brutalist cards, gauges, heatmap viewer, macro rings
│   │   ├── hooks/                  # usePredict, useHealth, useDarkMode
│   │   └── lib/                    # Typed API client and formatters
│   ├── package.json
│   ├── tailwind.config.js          # Custom neo-brutalist theme colors and hard box-shadows
│   └── vite.config.ts
├── notebooks/
│   ├── 01_dataset_eda_and_preprocessing.ipynb
│   ├── 02_mobilenetv3_finetuning.ipynb
│   ├── 03_gradcam_explainability.ipynb
│   └── 04_onnx_export_and_quantization.ipynb
├── scripts/
│   ├── build_notebooks.py          # Programmatic notebook generator
│   ├── run_notebooks.py            # Headless execution pipeline
│   ├── make_samples.py             # Deterministic sample extractor
│   └── validate_artifacts.py       # Artifact validation checks
├── start.bat / start.sh            # One-click dual-server launcher
├── setup.bat / setup.sh            # Dependency installer
└── README.md
```

---

## API Endpoints

* **`GET /api/health`**
  Returns model status, loaded runtime engines, class count, uptime, and system versions.
* **`POST /api/predict`**
  Accepts an image upload (`multipart/form-data`) and query parameters:
  * `top_k` (1 to 5, default 3)
  * `gradcam` (bool, default true)
  * `engine` (`onnx_fp32`, `onnx_int8_static`, `onnx_int8_dynamic`, `pytorch`)
  * `servings` (0.25 to 10.0, default 1.0)
  * `gradcam_class` (optional dish name to explain instead of top-1)
* **`GET /api/nutrition/{dish_name}`**
  Returns per-serving nutrition for a dish, scaled by the `servings` parameter.

Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

---

## Testing

* **Backend Suite:**
  ```bash
  .venv\Scripts\pytest.exe backend\tests -v
  # 27 passed (health checks, validation, Grad-CAM properties, triage boundaries, parity)
  ```
* **Frontend Verification:**
  ```bash
  cd frontend
  npm run typecheck    # TypeScript strict check (0 errors)
  npm run lint         # ESLint 9 (0 errors)
  npm run test         # Vitest unit & component tests (18 passed)
  npm run build        # Production bundle build
  ```

---

## License & Medical Disclaimer

Distributed under the MIT License.

*Medical Disclaimer:* Nutrition and portion estimates provided by CalorieCAM are approximations based on standard reference serving sizes. They are intended for informational purposes only and do not constitute professional dietary or medical advice.
