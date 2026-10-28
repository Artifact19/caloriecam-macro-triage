# PROJECT_SPEC.md — Visual Meal Recognition & Macro Triage Platform

> **Audience:** AI coding agent (Antigravity IDE). Implement everything in this document end to end.
> **Hard constraints:** 100% local, free, offline-capable. **No Streamlit.** No paid services. No API key required for any default feature.
> **Rule of thumb:** If this spec is silent, choose the simplest option that satisfies the Acceptance Criteria (Section 14) and record the decision in `docs/DECISIONS.md`.

---

## 0. Agent Operating Rules

1. Work in the phases of Section 13 in order. Do not start a phase until the previous phase's exit check passes.
2. Never fabricate results. Any metric, latency or accuracy figure shown in the UI, README or notebooks must come from a real measured run stored in `models/metrics.json` and `models/benchmark.json`. Numbers in this spec (e.g., "34ms") are **illustrative placeholders only**.
3. Pinned versions in Section 11 are targets. If a pin is unavailable for the user's platform/Python, use the nearest compatible version and record it in `docs/DECISIONS.md`.
4. Every Python module has type hints and docstrings; every public API has a Pydantic schema; every notebook cell group has a Markdown header explaining the *why*.
5. Keep secrets out of the repo. The only optional secret is `USDA_API_KEY` (read from `.env`, never required).
6. Prefer small, testable functions. Backend business logic must be importable without starting the server (needed for tests and notebooks).

---

## 1. Product Overview

**Vision.** A local web app where a user drops or photographs a meal. The system:

1. classifies the dish (fine-tuned **MobileNetV3-Large**, 25 Food-101 classes),
2. explains the decision with a **Grad-CAM** heatmap,
3. returns a **macro breakdown** (calories, protein, carbs, fat, fiber) per standard serving, scalable by portion,
4. reports honest local **latency telemetry**,
5. performs **triage**: when the model is unsure, the UI says so and shows alternatives instead of pretending certainty.

**Development philosophy.** Research is decoupled from production:

| Phase | Where | Output |
|---|---|---|
| Research / fine-tuning | `notebooks/` (Jupyter) | `models/*.pt`, `models/*.onnx`, `class_names.json`, `metrics.json`, `benchmark.json` |
| Production inference | `backend/` (FastAPI) + `frontend/` (React) | Serves artifacts from `models/`; never trains |

The backend only **consumes** artifacts; it must never import notebook code.

**Non-goals:** user accounts, cloud deployment, database, portion-size estimation from pixels, medical/dietary advice. The UI must display a disclaimer: *"Estimates are approximate and not medical advice."*

---

## 2. Repository Layout

```
meal-triage/
├── PROJECT_SPEC.md
├── README.md                      # quick start + screenshots + measured metrics
├── .env.example                   # USDA_API_KEY= (optional), ALLOWED_ORIGINS=...
├── .gitignore
├── run_backend.bat                # Windows
├── run_frontend.bat               # Windows
├── run_backend.sh                 # Linux/macOS
├── run_frontend.sh                # Linux/macOS
├── setup.bat / setup.sh           # one-shot env setup (Section 12)
├── docs/
│   └── DECISIONS.md
├── data/
│   ├── README.md
│   ├── download_food101.py        # automated Food101 download + subset manifest
│   ├── subset_classes.json        # the 25 target classes (Section 3)
│   ├── splits.json                # produced by notebook 01 (train/val indices)
│   └── raw/                       # torchvision download root (gitignored)
├── assets/
│   ├── nutrition_registry.json    # Section 4
│   ├── nutrition_registry.schema.json
│   ├── usda_fallback.py           # optional online fallback (Section 4.3)
│   └── samples/                   # 4 sample images: pizza.jpg, salad.jpg, steak.jpg, curry.jpg
├── notebooks/
│   ├── 01_dataset_eda_and_preprocessing.ipynb
│   ├── 02_mobilenetv3_finetuning.ipynb
│   ├── 03_gradcam_explainability.ipynb
│   ├── 04_onnx_export_and_quantization.ipynb
│   └── _shared/                   # tiny reusable .py helpers imported by notebooks
│       ├── __init__.py
│       ├── paths.py               # resolves repo root, models/, data/
│       ├── datasets.py            # Food25 Dataset class
│       └── transforms.py          # Albumentations builders
├── models/                        # artifacts (gitignored except .gitkeep and metrics json)
│   ├── mobilenetv3_food25.pt          # state_dict + metadata
│   ├── mobilenetv3_food25_fp32.onnx
│   ├── mobilenetv3_food25_int8_dynamic.onnx
│   ├── mobilenetv3_food25_int8_static.onnx
│   ├── class_names.json
│   ├── metrics.json                   # val/test top-1, macro-F1, per-class F1
│   └── benchmark.json                 # latency FP32 vs INT8
├── scripts/
│   ├── make_samples.py            # copies 4 sample images from Food101 test split into assets/samples
│   ├── run_notebooks.py           # executes notebooks 01→04 headlessly via nbconvert
│   └── validate_artifacts.py      # checks models/ + assets/ consistency (Section 9)
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app factory, CORS, lifespan (model warmup)
│   │   ├── config.py              # pydantic-settings
│   │   ├── schemas.py             # request/response models
│   │   ├── api/
│   │   │   ├── predict.py
│   │   │   ├── nutrition.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── preprocessing.py   # PIL → tensor/ndarray (must mirror notebook eval transform)
│   │   │   ├── onnx_engine.py     # ONNX Runtime session wrapper
│   │   │   ├── torch_engine.py    # PyTorch model + Grad-CAM
│   │   │   ├── gradcam.py
│   │   │   ├── nutrition.py       # registry loader, scaling, fallback
│   │   │   └── triage.py          # confidence policy
│   │   └── utils/
│   │       ├── images.py          # validation, resize, base64 PNG encode
│   │       └── timing.py          # perf_counter context manager
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_health.py
│   │   ├── test_predict.py
│   │   ├── test_nutrition.py
│   │   ├── test_preprocessing_parity.py
│   │   └── fixtures/ (small test jpgs)
│   ├── requirements.txt
│   └── requirements-dev.txt
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts             # dev proxy /api → http://127.0.0.1:8000
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── tsconfig.json
    ├── public/samples/            # copies of the 4 sample images served statically
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css              # Tailwind directives + CSS variables
        ├── lib/api.ts             # typed fetch client
        ├── lib/types.ts           # mirrors backend schemas
        ├── hooks/usePredict.ts
        └── components/
            ├── Header.tsx
            ├── UploadZone.tsx
            ├── SampleGallery.tsx
            ├── ConfidenceGauge.tsx
            ├── HeatmapViewer.tsx
            ├── NutritionCard.tsx
            ├── MacroRings.tsx
            ├── TopKList.tsx
            ├── TriageBanner.tsx
            ├── TelemetryBadge.tsx
            ├── PortionControl.tsx
            └── ErrorState.tsx / Skeletons.tsx
```

`.gitignore` must exclude: `data/raw/`, `models/*.pt`, `models/*.onnx`, `node_modules/`, `.venv/`, `__pycache__/`, `.env`, `.ipynb_checkpoints/`. **Keep** `models/metrics.json` and `models/benchmark.json` tracked.

---

## 3. Dataset & Class Subset

Use `torchvision.datasets.Food101(root="data/raw", split=..., download=True)` (101 classes, 750 train / 250 test images per class).

**Target subset — exactly 25 classes** (Food-101 label names; stored in `data/subset_classes.json` in this order, which defines the model's output index order and is the single source of truth):

```
pizza, caesar_salad, greek_salad, steak, chicken_curry, hamburger,
french_fries, sushi, ramen, spaghetti_bolognese, tacos, fried_rice,
pancakes, waffles, ice_cream, chocolate_cake, omelette, guacamole,
hot_dog, lasagna, samosa, hummus, pad_thai, donuts, grilled_salmon
```

Sample-image mapping for the UI (Section 7.1): Pizza → `pizza`, Salad → `greek_salad`, Steak → `steak`, Curry → `chicken_curry`.

### `data/download_food101.py`
- CLI: `python data/download_food101.py [--root data/raw] [--classes data/subset_classes.json]`.
- Downloads both splits (idempotent; skips if already present and checksum-OK via torchvision's internal check).
- Resolves subset class names → Food101 label indices using `dataset.classes`; **fail loudly** if any name is missing.
- Writes `data/subset_manifest.json`: `{class_name: {food101_idx, train_count, test_count}}`.
- Prints expected disk usage (~5 GB full dataset) before downloading and asks for confirmation unless `--yes`.
- Importable function `get_subset_samples(split) -> list[(path, new_label)]` reused by notebooks via `notebooks/_shared/datasets.py`.

### `scripts/make_samples.py`
Deterministically (seed 42) picks one **test-split** image for each of the 4 sample classes and saves to `assets/samples/{pizza,salad,steak,curry}.jpg` (resized so the longer side ≤ 1024 px, JPEG quality 90) and copies to `frontend/public/samples/`. Samples must be **correctly classified by the final model** ideally; the script accepts `--require-correct` which re-samples (up to 50 tries per class) until the trained ONNX model predicts the right class.

---

## 4. Nutrition Registry

### 4.1 `assets/nutrition_registry.json`

Schema (validated by `nutrition_registry.schema.json` and `scripts/validate_artifacts.py`):

```json
{
  "version": "1.0",
  "disclaimer": "Approximate values per standard serving; typical USDA-style estimates, ±15%. Not medical advice.",
  "items": {
    "pizza": {
      "display_name": "Pizza",
      "serving_description": "1 slice (107 g)",
      "serving_grams": 107,
      "calories_kcal": 285,
      "protein_g": 12,
      "carbs_g": 36,
      "fat_g": 10,
      "fiber_g": 2.5,
      "source": "usda_approx"
    }
  }
}
```

**Populate all 25 classes with these values** (agent: cross-check against USDA FoodData Central docs if online; if any value deviates >10% from what you can verify, prefer the verified value and note it in `docs/DECISIONS.md`):

| class | serving | g | kcal | P | C | F | fiber |
|---|---|---|---|---|---|---|---|
| pizza | 1 slice | 107 | 285 | 12 | 36 | 10 | 2.5 |
| caesar_salad | 1 bowl | 200 | 310 | 8 | 12 | 26 | 2 |
| greek_salad | 1 bowl | 250 | 230 | 6 | 12 | 18 | 3 |
| steak | 1 sirloin, cooked | 170 | 330 | 46 | 0 | 15 | 0 |
| chicken_curry | 1 cup | 250 | 330 | 24 | 12 | 20 | 3 |
| hamburger | 1 burger | 220 | 540 | 28 | 42 | 28 | 2 |
| french_fries | 1 medium | 117 | 365 | 4 | 48 | 17 | 4 |
| sushi | 6 pieces | 180 | 260 | 9 | 48 | 4 | 2 |
| ramen | 1 bowl | 450 | 450 | 18 | 60 | 16 | 3 |
| spaghetti_bolognese | 1 plate | 350 | 570 | 28 | 70 | 20 | 6 |
| tacos | 2 tacos | 170 | 340 | 16 | 28 | 18 | 4 |
| fried_rice | 1 cup | 200 | 330 | 8 | 50 | 11 | 2 |
| pancakes | 3 pancakes | 150 | 330 | 9 | 50 | 11 | 2 |
| waffles | 2 waffles | 150 | 430 | 10 | 54 | 20 | 2 |
| ice_cream | 1 cup | 132 | 270 | 5 | 31 | 14 | 1 |
| chocolate_cake | 1 slice | 100 | 380 | 5 | 50 | 18 | 3 |
| omelette | 3-egg | 180 | 300 | 20 | 3 | 23 | 0 |
| guacamole | ½ cup | 120 | 200 | 2 | 10 | 17 | 7 |
| hot_dog | 1 with bun | 150 | 300 | 11 | 24 | 18 | 1 |
| lasagna | 1 piece | 300 | 490 | 28 | 45 | 22 | 4 |
| samosa | 2 pieces | 120 | 300 | 5 | 32 | 17 | 3 |
| hummus | ½ cup | 120 | 210 | 6 | 17 | 13 | 6 |
| pad_thai | 1 plate | 300 | 560 | 20 | 70 | 22 | 4 |
| donuts | 1 glazed | 60 | 260 | 3 | 30 | 14 | 1 |
| grilled_salmon | 1 fillet | 150 | 310 | 34 | 0 | 19 | 0 |

`display_name` = title-cased, underscores → spaces (override: "Hot Dog", "Pad Thai").

**Consistency check** (in `validate_artifacts.py`): `abs(4*P + 4*C + 9*F − kcal) / kcal ≤ 0.12` for every item; otherwise warn.

### 4.2 Registry service (`backend/app/services/nutrition.py`)
- Loaded once at startup; keys must equal `class_names.json` exactly (startup fails with a clear message otherwise).
- `get_nutrition(dish, servings: float = 1.0)` scales all numeric fields linearly; `servings` bounded to `0.25 ≤ servings ≤ 10`.
- Also returns `macro_energy_split`: percentage of calories from protein/carbs/fat computed from 4/4/9 kcal/g, normalized to 100.

### 4.3 Optional USDA fallback (`assets/usda_fallback.py`)
- **Disabled by default.** Activated only if `USDA_API_KEY` is set **and** the requested dish is not in the registry (cannot happen for the 25 model classes; applies to `/nutrition/{dish_name}` free-text queries).
- Calls `https://api.nal.usda.gov/fdc/v1/foods/search` (FoodData Central), takes the top Foundation/SR Legacy match, maps nutrient numbers (208 energy kcal, 203 protein, 205 carbs, 204 fat, 291 fiber), per 100 g, and scales to a 100 g "serving" labeled `source: "usda_fdc_live"`.
- 3 s timeout; any failure → HTTP 404 with a friendly message. **No behavior depends on it.** Responses cached in-memory (LRU 256).
- Unit test uses a mocked HTTP response; no test may hit the network.

---

## 5. Notebooks (`notebooks/`)

**Global notebook standards**
- Cell 1: Markdown title, goal, inputs, outputs (files written), expected runtime (CPU vs GPU).
- Cell 2: Imports + `SEED = 42` + `seed_everything()` (python, numpy, torch, cuda, `torch.backends.cudnn.deterministic=True`).
- Cell 3: `from _shared.paths import ROOT, MODELS, DATA` (add `notebooks/` to `sys.path` if needed).
- Device selection: `cuda` → `mps` → `cpu`, printed explicitly.
- Every notebook must run **top-to-bottom with "Restart & Run All"** without edits, and in under the stated runtime. Executed outputs (plots, tables) must be saved in the committed `.ipynb`, except large image dumps.
- Use Markdown headers (`##`) per section and **LaTeX** (`$$ … $$`) for all math listed below.
- Generate the `.ipynb` files programmatically with `nbformat` (or edit via notebook tooling), then execute with `scripts/run_notebooks.py` to embed outputs.

### 5.1 `01_dataset_eda_and_preprocessing.ipynb`

**Sections**
1. **Load subset** via `_shared/datasets.py`; build a pandas DataFrame `(path, label, class_name, split)`.
2. **Class distribution analysis**: bar chart of counts per class (train/test); verify balanced (750/250). Report image-size distribution (width/height histograms), aspect-ratio stats, corrupted/unreadable file check, mean/std per channel computed on a 2,000-image sample (compare with ImageNet mean/std $\mu=[0.485,0.456,0.406]$, $\sigma=[0.229,0.224,0.225]$ — the model uses ImageNet stats; justify).
3. **Stratified split**: `sklearn.model_selection.StratifiedShuffleSplit(n_splits=1, test_size=0.1, random_state=42)` on the 18,750 train images → train (90 %) / val (10 %). Official Food-101 **test** split (6,250 images) is **held out** and used once at the end of notebook 02. Persist indices to `data/splits.json`. Assert stratification: per-class val count within ±1 of expected.
4. **Augmentation pipeline (Albumentations)** — define in `_shared/transforms.py` and import here:
   - Train: `LongestMaxSize(256)` → `RandomResizedCrop(224, scale=(0.6,1.0), ratio=(0.75,1.33))` → `HorizontalFlip(p=0.5)` → `Affine(scale=(0.9,1.1), translate_percent=(-0.05,0.05), rotate=(-15,15), p=0.7)` → `ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.05, p=0.8)` → `CoarseDropout(...)` optional p=0.2 → `Normalize(ImageNet)` → `ToTensorV2`.
   - Eval: `Resize(256)` → `CenterCrop(224)` → `Normalize` → `ToTensorV2`. **This is the production transform**; backend preprocessing must be numerically identical (see parity test, Section 9).
   - **CutMix**: Albumentations has no batch-level CutMix, so implement it at batch level using `torchvision.transforms.v2.CutMix(num_classes=25, alpha=1.0)` applied in the DataLoader `collate_fn` with probability 0.5. Document the math:
     $$\tilde{x} = M \odot x_A + (1-M)\odot x_B,\qquad \tilde{y} = \lambda y_A + (1-\lambda) y_B,\qquad \lambda \sim \mathrm{Beta}(\alpha,\alpha),\quad \lambda \approx 1 - \frac{\text{area}(B)}{H W}$$
   - Visualize: 4×4 grid of augmented samples for each of: ColorJitter-only, Affine-only, full pipeline, CutMix batch.
5. **Sanity**: dataloader throughput test (images/sec) with `num_workers` ∈ {0, 2, 4}; pick best; write to `notebooks/_shared/paths.py`-adjacent `config` note.
6. **Outputs:** `data/splits.json`, `models/class_names.json` (ordered list identical to `subset_classes.json`).

### 5.2 `02_mobilenetv3_finetuning.ipynb`

**Model:** `torchvision.models.mobilenet_v3_large(weights=MobileNet_V3_Large_Weights.IMAGENET1K_V2)`; replace `classifier[3]` (`Linear(1280, 1000)`) with `Linear(1280, 25)`; keep `Dropout(0.2)`.
(Document a one-line switch to `efficientnet_b0` for comparison; default stays MobileNetV3-Large because it is faster on CPU.)

**Loss/Math (LaTeX in Markdown)**
- Label-smoothed cross-entropy ($\varepsilon=0.1$, $K=25$): $$\mathcal{L}=-\sum_{k=1}^{K}\tilde{y}_k\log p_k,\quad \tilde{y}_k=(1-\varepsilon)y_k+\frac{\varepsilon}{K},\quad p_k=\frac{e^{z_k}}{\sum_j e^{z_j}}$$
  (With CutMix, targets are already soft; `nn.CrossEntropyLoss` accepts probability targets—apply smoothing only to hard-label batches.)
- Cosine LR schedule: $$\eta_t=\eta_{\min}+\tfrac12(\eta_{\max}-\eta_{\min})\bigl(1+\cos\tfrac{\pi t}{T}\bigr)$$ with linear warmup (1 epoch).
- F1: $$F_1^{(c)}=\frac{2\,P_cR_c}{P_c+R_c},\qquad F_1^{\text{macro}}=\frac1K\sum_c F_1^{(c)}$$

**Training recipe**
- **Phase A (head warm-up, 3 epochs):** backbone frozen (`requires_grad=False`, BatchNorm layers in eval mode), head LR $10^{-3}$.
- **Phase B (full fine-tune, 12 epochs):** unfreeze all. **Differential learning rates** via AdamW param groups: backbone `features` lr $=10^{-4}$, classifier lr $=10^{-3}$, weight decay 0.01 (no decay on bias/BN). Cosine schedule per group with 1-epoch warmup.
- Batch size 64 (auto-reduce on CUDA OOM), gradient clipping `clip_grad_norm_(…, 1.0)`.
- **FP16 mixed precision:** `torch.autocast(device_type="cuda", dtype=torch.float16)` + `torch.amp.GradScaler("cuda")` with the canonical `scaler.scale(loss).backward(); scaler.unscale_(opt); clip; scaler.step(opt); scaler.update()` sequence. On CPU/MPS: autocast disabled (or bf16 on CPU if supported), code path must still run. Include a Markdown explanation of loss scaling.
- **Validation each epoch:** loss, top-1, top-3, **macro-F1** (`sklearn.metrics.f1_score(average="macro")`), per-class F1 table. Log to a pandas DataFrame and plot curves (loss, accuracy, F1, LR).
- **Checkpointing:** save best-by-val-macro-F1 to `models/mobilenetv3_food25.pt` as `{"state_dict":…, "class_names":…, "arch":"mobilenet_v3_large", "img_size":224, "mean":…, "std":…, "val_macro_f1":…, "epoch":…}`. Early stopping patience 4.
- **Final evaluation (once):** load best checkpoint, evaluate on the held-out test split: top-1, top-3, macro-F1, confusion matrix heatmap, top-10 most confused class pairs, and **reliability diagram + ECE** (expected calibration error, 15 bins) — needed to justify the triage threshold. Optionally fit temperature scaling $T$ on the val set: $p_k=\mathrm{softmax}(z/T)$; store `temperature` in the checkpoint metadata; backend applies it.
- **Outputs:** `models/mobilenetv3_food25.pt`, `models/metrics.json` (`val_macro_f1`, `test_top1`, `test_top3`, `test_macro_f1`, `ece`, `temperature`, `per_class_f1`, `training_config`, `device`, `date`).
- Expected runtime: ≲ 45 min on a mid-range GPU; document CPU runtime and provide a `FAST_DEV=True` flag (3 epochs, 200 imgs/class) for smoke testing.
- Target (non-binding): test top-1 ≥ 85 %, macro-F1 ≥ 0.84. Report whatever is actually achieved.

### 5.3 `03_gradcam_explainability.ipynb`

**Math (LaTeX)** — for target class $c$ and last-conv feature maps $A^k\in\mathbb{R}^{u\times v}$:
$$\alpha_k^c=\frac{1}{Z}\sum_{i}\sum_{j}\frac{\partial y^c}{\partial A^k_{ij}},\qquad L^c_{\text{Grad-CAM}}=\mathrm{ReLU}\Bigl(\sum_k \alpha_k^c A^k\Bigr)$$
Normalization: $\hat L=\dfrac{L-\min L}{\max L-\min L+\epsilon}$.

**Implementation requirements**
- Target layer: `model.features[-1]` (final Conv-BN-Hardswish block, 960 channels, 7×7 spatial at 224 input).
- **Hooks:** register a *forward hook* that stores the activation and calls `output.register_hook(...)` to capture its gradient (this avoids the known in-place/`register_backward_hook` pitfalls). Before running, set every `nn.Hardswish`/`nn.ReLU`/`nn.Hardsigmoid` `inplace=False` (helper `disable_inplace(model)`). Model in `eval()`, **fp32**, gradients enabled only for the pass.
- Compute $y^c$ as the **pre-softmax logit** of the target class (default: predicted class; optional: user-selected class).
- Pipeline: gradients → global-average-pool → weighted sum of activations → ReLU → min-max normalize → resize to original image size with `cv2.resize(..., INTER_CUBIC)` → optional Gaussian blur (k=5) → `cv2.applyColorMap(…, COLORMAP_JET)` → convert BGR→RGB → blend `cv2.addWeighted(img, 1-α, heat, α, 0)`.
- **Remove hooks** after use (`handle.remove()`), implemented as a context manager `GradCAM(model, layer)` with `__enter__/__exit__`.
- **Verification cells (must exist):**
  1. Shape/finite checks (no NaN; heatmap in [0,1]).
  2. Sanity: Grad-CAM for target class vs. a different class yields different maps (mean absolute difference > threshold).
  3. **Deletion test:** blank the top-20 % hottest pixels and show the target-class probability drops on average over 100 test images (report mean drop).
  4. Gallery: 4 × (original, heatmap, overlay) per sample class; a "failure case" gallery of 6 misclassified test images with commentary.
- Export `backend`-ready reference implementation in this notebook's final cell, **identical** to `backend/app/services/gradcam.py` (the backend file is the canonical one; the notebook imports nothing from backend but must produce the same output; test in Section 9).

### 5.4 `04_onnx_export_and_quantization.ipynb`

1. **Export FP32:** `torch.onnx.export(model.eval(), dummy(1,3,224,224), "models/mobilenetv3_food25_fp32.onnx", input_names=["input"], output_names=["logits"], opset_version=17, dynamic_axes={"input":{0:"batch"}, "logits":{0:"batch"}})`. Validate with `onnx.checker.check_model`; compare ONNX vs PyTorch logits on 64 test images: `max |Δ| < 1e-4`.
2. **Dynamic INT8:** `onnxruntime.quantization.quantize_dynamic(fp32, int8_dynamic, weight_type=QuantType.QUInt8)`. Explain in Markdown that dynamic quantization mainly quantizes MatMul/Gemm weights, so conv-heavy MobileNets may see **small or no speedup** — this must be verified by measurement, not assumed.
3. **Static INT8 (QDQ) — recommended path:** `quantize_static` with a `CalibrationDataReader` fed 200 val images (preprocessed by the eval transform), `quant_format=QuantFormat.QDQ`, `activation_type=QuantType.QUInt8`, `weight_type=QuantType.QInt8`, `per_channel=True`. Save `models/mobilenetv3_food25_int8_static.onnx`.
4. **Accuracy check:** evaluate FP32, INT8-dynamic, INT8-static on the full held-out test split: top-1, macro-F1. **Acceptance for selecting an INT8 model as production default: top-1 drop ≤ 1.0 percentage point vs FP32** and measurable speedup; otherwise default engine falls back to FP32 ONNX.
5. **Latency benchmarking (CPU):** `CPUExecutionProvider`, `intra_op_num_threads` ∈ {1, 4, all}, batch size 1, 20 warmup + 200 timed runs using `time.perf_counter`; report mean, p50, p95, p99 (ms), throughput, and model file size (MB) in a table and bar chart for: PyTorch FP32 (CPU), ONNX FP32, ONNX INT8-dynamic, ONNX INT8-static. Record CPU model, core count, OS, ORT version.
6. **Outputs:** the three `.onnx` files, `models/benchmark.json` (`{engine: {mean_ms, p50_ms, p95_ms, p99_ms, size_mb, top1, macro_f1}}`, plus `default_engine` key chosen by the rule in step 4), and update `models/metrics.json` with quantization accuracies.
7. Write `models/class_names.json` check and include the preprocessing contract (resize 256 → center-crop 224 → /255 → ImageNet normalize → NCHW float32) as a Markdown cell.

---

## 6. Backend (`backend/`)

**Stack:** Python 3.10–3.12, FastAPI, Uvicorn, ONNX Runtime (CPU), PyTorch (CPU build is sufficient), Pillow, OpenCV (headless), NumPy.

### 6.1 Configuration (`config.py`, pydantic-settings, `.env` supported)
| Var | Default | Meaning |
|---|---|---|
| `MODELS_DIR` | `../models` | artifact dir |
| `ASSETS_DIR` | `../assets` | registry dir |
| `DEFAULT_ENGINE` | read from `benchmark.json.default_engine`, else `onnx_fp32` | `onnx_int8_static` \| `onnx_int8_dynamic` \| `onnx_fp32` \| `pytorch` |
| `CONF_THRESHOLD_HIGH` | `0.70` | confident |
| `CONF_THRESHOLD_LOW` | `0.40` | below → "uncertain" |
| `MAX_UPLOAD_MB` | `10` | |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | CORS |
| `USDA_API_KEY` | *(unset)* | optional fallback |
| `ORT_INTRA_OP_THREADS` | `0` (auto) | |

### 6.2 Startup (lifespan)
1. Load `class_names.json`, `metrics.json`, `benchmark.json`, nutrition registry; validate key sets match.
2. Create ONNX Runtime sessions for available `.onnx` files (lazy for unused engines), `SessionOptions.graph_optimization_level = ORT_ENABLE_ALL`.
3. Load the PyTorch checkpoint (used for Grad-CAM and the optional `pytorch` engine), `eval()`, disable in-place activations.
4. **Warm-up:** run one dummy inference on every loaded engine (and one Grad-CAM pass) so first-request latency is representative.
5. If artifacts are missing: the app **still starts**, `/health` reports `model_loaded:false` with the list of missing files, and `/predict` returns `503` with message *"Model artifacts not found. Run notebooks 01–04 (python scripts/run_notebooks.py)."*

### 6.3 Endpoints (all under no prefix; Vite proxies `/api/*` → backend with prefix stripped, or mount routers at both `/` and `/api`; choose mounting at `/api` and call `/api/...` from the frontend. The three required paths are therefore `/api/health`, `/api/predict`, `/api/nutrition/{dish_name}`; also expose the same routes un-prefixed for curl convenience.)

#### `GET /health`
```json
{
  "status": "ok",
  "model_loaded": true,
  "engines": ["onnx_int8_static", "onnx_fp32", "pytorch"],
  "default_engine": "onnx_int8_static",
  "num_classes": 25,
  "classes": ["pizza", "..."],
  "model_version": "mobilenetv3_large-food25-<val_macro_f1>",
  "onnxruntime_version": "…",
  "torch_version": "…",
  "uptime_s": 123.4,
  "missing_artifacts": []
}
```

#### `POST /predict` (multipart/form-data)
- Field `file`: image (`image/jpeg`, `image/png`, `image/webp`). 
- Query params: `top_k` (int 1–5, default 3), `gradcam` (bool, default true), `engine` (optional override), `servings` (float, default 1.0), `gradcam_class` (optional class name to explain instead of top-1).
- **Validation:** content-type allowlist; size ≤ `MAX_UPLOAD_MB` (413); decode with Pillow, `Image.verify()` then reopen; apply `ImageOps.exif_transpose`; convert to RGB; reject images < 64 px on the short side (422); cap decompression bombs (`Image.MAX_IMAGE_PIXELS = 50_000_000`). Never write uploads to disk.
- **Flow:** preprocess → classification on the chosen engine → temperature-scaled softmax → top-k → triage → nutrition lookup → (if `gradcam`) Grad-CAM on PyTorch FP32 (always PyTorch; ONNX cannot provide gradients) → timing.
- **Response (`PredictResponse`):**
```json
{
  "top1": {"label": "pizza", "display_name": "Pizza", "confidence": 0.9123},
  "topk": [
    {"label": "pizza", "display_name": "Pizza", "confidence": 0.9123},
    {"label": "lasagna", "display_name": "Lasagna", "confidence": 0.0411}
  ],
  "triage": {
    "level": "confident",             // "confident" | "review" | "uncertain"
    "message": "High confidence prediction.",
    "alternatives_with_nutrition": []   // filled when level != "confident": top-3 w/ kcal & macros
  },
  "nutrition": {
    "dish": "pizza", "display_name": "Pizza",
    "serving_description": "1 slice (107 g)", "servings": 1.0,
    "calories_kcal": 285, "protein_g": 12, "carbs_g": 36, "fat_g": 10, "fiber_g": 2.5,
    "macro_energy_split": {"protein_pct": 16.8, "carbs_pct": 50.5, "fat_pct": 32.7},
    "source": "usda_approx"
  },
  "gradcam": {
    "target_class": "pizza",
    "heatmap_png_base64": "<RGBA PNG, jet colormap, alpha = normalized intensity>",
    "overlay_png_base64": "<RGB PNG, pre-blended at alpha 0.5>",
    "width": 512, "height": 384
  },
  "latency": {
    "preprocess_ms": 4.1, "inference_ms": 11.3, "gradcam_ms": 38.0,
    "postprocess_ms": 2.2, "total_ms": 55.6,
    "classification_path_ms": 17.6      // preprocess + inference + postprocess (excludes Grad-CAM)
  },
  "engine": "onnx_int8_static",
  "model_version": "…",
  "image": {"original_width": 1600, "original_height": 1200}
}
```
- Returned heat/overlay images are downscaled so the longer side ≤ 512 px (keeps payload small).
- `total_ms` = server-side wall-clock from request body fully received to response model built (use `time.perf_counter`). The UI shows both numbers honestly (Section 7.4).
- **Triage policy (`triage.py`):** `confidence ≥ HIGH` → `confident`; `LOW ≤ conf < HIGH` → `review` ("Moderately confident — check alternatives."); `< LOW` → `uncertain` ("Low confidence — the dish may not be among the 25 supported classes."). Both non-confident levels populate `alternatives_with_nutrition` with the top-3. Document in README that thresholds were chosen using the reliability diagram from notebook 02.

#### `GET /nutrition/{dish_name}`
- `dish_name`: case-insensitive; accepts `Chicken Curry`, `chicken-curry`, `chicken_curry` (normalize to snake_case).
- Query: `servings` (default 1.0, 0.25–10).
- 200 → same `nutrition` object as above. 404 → `{"detail": "Unknown dish 'x'. Known: [...]"}` (with registry fallback to USDA only if configured). `GET /nutrition` (no name) returns the list of all registry items (useful for the UI).

### 6.4 Core services — implementation notes
- **`preprocessing.py`**: PIL → resize shorter side to 256 (bicubic... **must match** the notebook's eval transform interpolation; the Albumentations `Resize/LongestMaxSize` vs. PIL difference is the most common parity bug) → center crop 224 → float32 /255 → normalize → NCHW. Use **one** implementation (cv2-based, shared semantic) and assert parity in tests (Section 9). Simplest robust approach: implement the eval transform with `cv2.resize(..., interpolation=cv2.INTER_LINEAR)` in both notebook (`_shared/transforms.py::eval_numpy`) and backend.
- **`onnx_engine.py`**: class `OnnxEngine(path, threads)`, `.predict_logits(batch: np.ndarray) -> np.ndarray`; thread-safe (ORT sessions are thread-safe for `run`).
- **`torch_engine.py`**: `torch.set_num_threads(min(4, cpu_count))`; `@torch.inference_mode()` for plain classification; Grad-CAM uses `torch.enable_grad()`. Guard Grad-CAM with a `threading.Lock` (hooks are per-model state) and run blocking inference in `anyio.to_thread` / `run_in_threadpool` so the event loop stays responsive.
- **`gradcam.py`**: as specified in Section 5.3 (context-managed hooks, no leaks: a test must call Grad-CAM 20× and assert `len(layer._forward_hooks) == 0` afterward).
- **Logging:** structured logs (`logging` stdlib): request id, engine, latency breakdown, predicted label; no image data logged.
- **Errors:** consistent JSON `{ "detail": str, "code": str }`; global exception handler returns 500 without stack traces.
- **OpenAPI:** auto docs at `/docs`; tag endpoints; include response examples.

---

## 7. Frontend (`frontend/`)

**Stack:** React 18 + TypeScript, Vite, Tailwind CSS 3, lucide-react, Framer Motion, Recharts. **No Streamlit, no Gradio, no server-rendered UI.** Dark mode is the default.

### 7.0 Design system
- Dark theme: background `#0B0F14` (near-black slate), surface cards `#111823` with 1 px `white/8` borders, `rounded-2xl`, soft shadow; accent gradient emerald→cyan (`from-emerald-400 to-cyan-400`); macro colors: **Protein `#38BDF8`** (sky), **Carbs `#FBBF24`** (amber), **Fat `#F472B6`** (pink), **Fiber `#34D399`**.
- Typography: Inter (self-host via `@fontsource/inter` — no CDN, offline-capable); tabular numerals for metrics.
- Light-mode toggle (sun/moon icon) is optional; the preference persists in `localStorage`; default `dark`. Use Tailwind `darkMode: "class"`.
- Mobile-first responsive: single column < 768 px; two-column ≥ `lg`. Touch targets ≥ 44 px. On mobile the upload zone offers camera capture: `<input type="file" accept="image/*" capture="environment">` via a "Take photo" button (in addition to the file picker).
- Accessibility: all interactive elements keyboard reachable with visible focus rings; `aria-live="polite"` region announcing the result; heatmap slider has `aria-label`; color is never the only signal; respects `prefers-reduced-motion` (disable Framer Motion animations).
- Fully offline: no external fonts/CDN/analytics.

### 7.1 Image intake
- **`UploadZone`**: drag-and-drop area (visual state change on drag-over via Framer Motion), click-to-browse, paste from clipboard (Ctrl/Cmd+V), client-side validation (type jpeg/png/webp, ≤ 10 MB) with inline error messages. Live preview with filename, dimensions, size, and "Remove / Replace" buttons.
- **`SampleGallery`**: 4 quick-select buttons — **Pizza, Salad, Steak, Curry** — thumbnails from `/samples/*.jpg`; clicking fetches the static file, converts to a `File`, and runs the exact same prediction path as an upload. Selected sample gets a ring highlight.
- Auto-run prediction on image selection (debounced, aborts in-flight request via `AbortController`), plus a "Re-analyze" button. Servings are controlled separately (7.3) and do **not** re-run inference — they re-fetch `/api/nutrition/{dish}?servings=` (or scale locally from the response; choose local scaling to avoid extra calls, but keep the API for parity).

### 7.2 Inference dashboard layout
1. **Top-1 card**: dish display name (large), `ConfidenceGauge` (semi-circular or radial gauge, animated 0→value with Framer Motion; color by triage level: emerald ≥ 70 %, amber 40–70 %, rose < 40 %), and the engine badge ("INT8 · static").
2. **`TriageBanner`** (only if `level != confident`): amber/rose banner with the message plus a list of alternatives, each a clickable chip showing name, confidence and kcal; clicking an alternative swaps the nutrition card to that dish (and re-requests Grad-CAM for that class using `gradcam_class`), clearly labeled "Viewing alternative".
3. **`HeatmapViewer`**: side-by-side **Original vs. Grad-CAM Attention** on `md+`; stacked tabs on mobile. The heatmap layer is the returned RGBA PNG stacked over the original with CSS `opacity` controlled by a **slider (0–100 %, default 55 %)**. Include a "compare" mode: a draggable split-reveal handle (optional, nice-to-have), a legend bar (blue→red = low→high attention), and a tooltip explaining Grad-CAM in one sentence. If `gradcam` is null (disabled/failed), show a graceful placeholder.
4. **`NutritionCard`**: 
   - Large total calories (animated count-up), serving description.
   - `MacroRings`: three concentric/adjacent **circular progress rings** (Recharts `RadialBarChart`) for Protein/Carbs/Fat, showing grams in the center label and each as % of macro calories; plus a stacked horizontal **macro bar distribution** below. Fiber shown as a small chip.
   - `PortionControl`: stepper (0.5 ×, 1 ×, 1.5 ×, 2 ×, custom) that scales all numbers live.
   - Footer disclaimer: "Estimates are approximate and not medical advice."
5. **`TopKList`**: top-3 horizontal bars with percentages.
6. **`TelemetryBadge`** (see 7.4).

### 7.3 States
- **Empty**: hero with instructions + samples.
- **Loading**: skeleton shimmer for all cards + animated progress; cancel button.
- **Success**: staggered entrance (Framer Motion `staggerChildren`).
- **Backend unreachable**: poll `/api/health` on load; if it fails show a full-width banner with the exact command to start the backend (`run_backend.bat` / `./run_backend.sh`). If `model_loaded=false`, show the "run notebooks" instructions from `missing_artifacts`.
- **Errors**: typed handling for 413/415/422/503/network with friendly copy and a retry action.

### 7.4 Telemetry badge
Displays measured values from the response, e.g. `⚡ Ingest to Output: {total_ms} ms` with an expandable popover showing the breakdown (preprocess / inference / Grad-CAM / postprocess), engine used, and `classification_path_ms` ("Classification only: X ms"). Also measure and show **client round-trip** (`performance.now()` around the fetch) labeled "Round-trip". Use tabular-nums, round to 1 decimal. **Never hard-code a latency value.**

### 7.5 Frontend implementation notes
- `lib/api.ts`: typed `predict(file, opts, signal)`, `getNutrition(dish, servings)`, `getHealth()`; base URL `"/api"`; Vite dev proxy in `vite.config.ts`: `server.proxy['/api'] = { target: 'http://127.0.0.1:8000', changeOrigin: true }`.
- State: React hooks only (`useReducer` in `usePredict`); no Redux needed.
- `lib/types.ts` mirrors the Pydantic schema exactly.
- Base64 PNGs rendered as `data:image/png;base64,…` `<img>` with `object-contain`, same aspect ratio box as the original so the overlay aligns pixel-perfectly (use a single relatively-positioned container with `aspect-ratio` from `image.original_width/height`).
- Production build: `npm run build` produces `dist/`; optional `backend` static mount: if `frontend/dist` exists, FastAPI serves it at `/` so the whole app can run with one process (`run_backend` prints both URLs). Dev mode uses Vite on `:5173`.
- Lint/format: ESLint + Prettier configs; `npm run typecheck` (`tsc --noEmit`) must pass.

---

## 8. Data Flow (reference)

```
Browser ──multipart──► POST /api/predict
   │                       │
   │                 validate+decode (Pillow, EXIF-fix)
   │                       │
   │                 eval transform (resize256→crop224→norm)
   │                       │
   │              ┌────────┴─────────┐
   │              ▼                  ▼
   │     ONNX INT8/FP32       PyTorch FP32 (+hooks)
   │     logits → softmax/T   Grad-CAM heatmap
   │              │                  │
   │         triage + nutrition      │
   │              └────────┬─────────┘
   ◄────── JSON (top-k, triage, macros, heatmap PNGs, latency) ──────
```

---

## 9. Testing & Verification

**Backend (`pytest`, `httpx`/`TestClient`)** — all tests run offline.
- `test_health.py`: 200 and schema; behavior when artifacts missing (monkeypatch dir) → `model_loaded:false`, predict → 503.
- `test_predict.py`: each of the 4 sample images returns a valid schema; top-1 correct for the samples (skip with clear reason if artifacts absent); rejects: non-image bytes (415/422), > 10 MB (413), 10×10 px (422), truncated JPEG (422); EXIF-rotated image handled; `gradcam=false` omits the key; `engine` override works; `top_k` bounds.
- `test_nutrition.py`: all 25 classes present; name normalization variants; scaling math (`servings=2` doubles values); 404 for unknown; USDA fallback only with mocked HTTP.
- `test_preprocessing_parity.py`: backend preprocessing vs notebook `_shared/transforms.py::eval_numpy` on 5 fixture images → `np.allclose(atol=1e-5)`. Also ONNX FP32 logits vs PyTorch logits `atol=1e-3`.
- Grad-CAM tests: output shape, range [0,1], no hook leaks over 20 calls, determinism across two runs.
- Triage unit tests at boundary values (0.39999, 0.4, 0.69999, 0.7).

**`scripts/validate_artifacts.py`** (exit code ≠ 0 on failure): all expected files exist; `class_names.json` == `subset_classes.json`; registry keys == class names; calorie-consistency check; ONNX models load and output shape `(1, 25)`; `benchmark.json` and `metrics.json` have required keys.

**Frontend:** `npm run typecheck`, `npm run lint`, `npm run build` must pass. Add Vitest + React Testing Library smoke tests for `ConfidenceGauge`, `NutritionCard` scaling, and `usePredict` error mapping (mock `fetch`). Optional: one Playwright e2e that uploads a sample and asserts the dashboard renders (skippable if browsers aren't installed).

---

## 10. Security & Robustness
- Backend binds to `127.0.0.1` by default (not `0.0.0.0`); document the LAN option (for phone testing on the same Wi-Fi: `--host 0.0.0.0` plus adding the origin to `ALLOWED_ORIGINS`).
- CORS restricted to configured origins; no wildcard in default config.
- Uploads processed in memory only; image bytes never logged or persisted.
- Request size limit enforced while streaming (reject early rather than reading all bytes).
- Dependency hygiene: no unpinned `latest`; `pip check` passes.
- No telemetry, no analytics, no network calls at runtime (except the optional USDA fallback when explicitly configured).

---

## 11. Dependencies (pinned targets)

### `backend/requirements.txt`
```
fastapi==0.115.6
uvicorn[standard]==0.32.1
python-multipart==0.0.20
pydantic==2.10.3
pydantic-settings==2.7.0
pillow==11.0.0
numpy==1.26.4
opencv-python-headless==4.10.0.84
onnx==1.17.0
onnxruntime==1.20.1
torch==2.5.1
torchvision==0.20.1
httpx==0.28.1
python-dotenv==1.0.1
```
CPU-only PyTorch install hint (smaller download), documented in README:
`pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu`
(GPU users training in notebooks install the CUDA build instead — documented, not required for serving.)

### `backend/requirements-dev.txt`
```
-r requirements.txt
pytest==8.3.4
pytest-asyncio==0.25.0
ruff==0.8.4
mypy==1.13.0
```

### `notebooks/requirements-notebooks.txt` (training/research env; may share the same venv)
```
-r ../backend/requirements.txt
albumentations==1.4.21
scikit-learn==1.5.2
pandas==2.2.3
matplotlib==3.9.3
seaborn==0.13.2
tqdm==4.67.1
jupyterlab==4.3.3
ipykernel==6.29.5
nbformat==5.10.4
nbconvert==7.16.4
onnxruntime==1.20.1
```
(`opencv-python-headless` and `albumentations` must not conflict; if Albumentations pulls `opencv-python`, uninstall it and keep the headless build, record in DECISIONS.md.)

### `frontend/package.json` (key parts)
```json
{
  "name": "meal-triage-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit",
    "lint": "eslint src --ext .ts,.tsx",
    "test": "vitest run"
  },
  "dependencies": {
    "@fontsource/inter": "5.1.0",
    "framer-motion": "11.15.0",
    "lucide-react": "0.468.0",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "recharts": "2.15.0"
  },
  "devDependencies": {
    "@testing-library/react": "16.1.0",
    "@types/react": "18.3.17",
    "@types/react-dom": "18.3.5",
    "@vitejs/plugin-react": "4.3.4",
    "autoprefixer": "10.4.20",
    "eslint": "9.17.0",
    "jsdom": "25.0.1",
    "postcss": "8.4.49",
    "prettier": "3.4.2",
    "tailwindcss": "3.4.17",
    "typescript": "5.7.2",
    "vite": "5.4.11",
    "vitest": "2.1.8"
  }
}
```
Commit `package-lock.json`. Use Tailwind **v3** (not v4) so `tailwind.config.js` + PostCSS setup above is valid.

---

## 12. Execution Playbook (local setup & run)

**Prerequisites:** Python 3.10–3.12, Node.js ≥ 18 (LTS), Git. ~8 GB free disk (dataset + envs). GPU optional (only speeds notebook 02).

### 12.1 Windows

**`setup.bat`**
```bat
@echo off
setlocal
cd /d "%~dp0"
if not exist .venv ( python -m venv .venv || goto :err )
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r backend\requirements.txt || goto :err
pip install -r notebooks\requirements-notebooks.txt || goto :err
pushd frontend
call npm ci || goto :err
popd
echo Setup complete. Next: run notebooks (python scripts\run_notebooks.py), then run_backend.bat and run_frontend.bat
exit /b 0
:err
echo Setup failed. See messages above.
exit /b 1
```

**`run_backend.bat`**
```bat
@echo off
setlocal
cd /d "%~dp0"
if not exist .venv ( echo Run setup.bat first. & exit /b 1 )
call .venv\Scripts\activate.bat
python scripts\validate_artifacts.py --warn-only
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**`run_frontend.bat`**
```bat
@echo off
setlocal
cd /d "%~dp0frontend"
if not exist node_modules ( call npm ci )
call npm run dev -- --host 127.0.0.1 --port 5173
```

### 12.2 Linux / macOS

**`setup.sh`**, **`run_backend.sh`**, **`run_frontend.sh`** — same logic using `python3 -m venv .venv`, `source .venv/bin/activate`, `npm ci`, `chmod +x` set; `set -euo pipefail` at the top. `run_backend.sh` runs `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`.

### 12.3 First-run sequence (document verbatim in README)
```
1.  setup.bat | ./setup.sh
2.  python data/download_food101.py            # downloads Food-101 (~5 GB) and builds the 25-class manifest
3.  python scripts/run_notebooks.py            # executes notebooks 01→04 headlessly (or open JupyterLab and Run All in order)
4.  python scripts/make_samples.py --require-correct
5.  python scripts/validate_artifacts.py
6.  run_backend.bat | ./run_backend.sh         # http://127.0.0.1:8000/docs
7.  run_frontend.bat | ./run_frontend.sh       # http://127.0.0.1:5173
```
`scripts/run_notebooks.py`: executes `01…04` sequentially with `nbconvert.preprocessors.ExecutePreprocessor(timeout=-1, kernel_name="python3")`, writes executed notebooks back in place, prints elapsed time per notebook, stops on first failure; supports `--fast` (sets env `FAST_DEV=1` that notebook 02 reads).

### 12.4 Offline guarantee
After step 2 (the only step needing internet, plus pip/npm installs), everything runs offline. Pretrained ImageNet weights are downloaded by torchvision on first use in notebook 02 and cached under `~/.cache/torch`; document this as a one-time download. The backend and frontend never fetch from the network at runtime.

---

## 13. Implementation Phases & Exit Checks

| # | Phase | Deliverables | Exit check |
|---|---|---|---|
| 0 | Scaffold | tree, configs, `.gitignore`, `.env.example`, scripts | `setup` script completes |
| 1 | Data | `download_food101.py`, `subset_classes.json`, `_shared/*` | manifest shows 25 classes × 750/250 |
| 2 | Notebook 01 | EDA, splits, transforms | `splits.json`, `class_names.json` exist; Restart & Run All passes |
| 3 | Notebook 02 | training + eval | `.pt` and `metrics.json` exist; real metrics recorded |
| 4 | Notebook 03 | Grad-CAM + verification cells | deletion test shows prob drop; hooks removed |
| 5 | Notebook 04 | ONNX, quantization, benchmark | 3 `.onnx` + `benchmark.json`; parity `< 1e-4` |
| 6 | Registry | `nutrition_registry.json` + schema | `validate_artifacts.py` passes |
| 7 | Backend | services, endpoints, tests | `pytest` green; `/docs` works; 4 samples classified |
| 8 | Frontend | all components & states | `typecheck`, `lint`, `build`, `test` green |
| 9 | Integration | samples, scripts, README | full first-run sequence works from a clean clone |
| 10 | Polish | a11y pass, reduced motion, error states, screenshots | Section 14 checklist all ✅ |

If the machine has no GPU and notebook 02 is too slow, run with `--fast` first to unblock phases 4–9, then retrain the full recipe and re-run 03–04 and `make_samples.py`.

---

## 14. Acceptance Criteria (definition of done)

**Functional**
- [ ] Drag-drop, file picker, clipboard paste and mobile camera capture all produce a prediction.
- [ ] The 4 sample buttons (Pizza, Salad, Steak, Curry) work and are correctly classified by the shipped model.
- [ ] Dashboard shows Top-1 with confidence gauge, side-by-side original/Grad-CAM with working opacity slider, macro rings + bars + calories, top-3 list, triage banner when applicable, and the telemetry badge with real measured numbers.
- [ ] Portion control scales calories and macros correctly.
- [ ] Low-confidence input (e.g., a photo of a car) triggers `uncertain` triage rather than a confident answer (verify manually; record the observed confidence in README).
- [ ] `/health`, `/predict`, `/nutrition/{dish_name}` behave exactly as specified in Section 6.3.

**Quality**
- [ ] Notebooks 01–04 each run top-to-bottom with no manual edits; contain Markdown headers and LaTeX for all equations listed above.
- [ ] Reported accuracy/F1/latency in README are copied from `metrics.json`/`benchmark.json` (no invented numbers).
- [ ] INT8 default selected by the rule in 5.4 (≤ 1 pp top-1 drop and measurable speedup), otherwise FP32 ONNX with an explanatory note.
- [ ] All tests in Section 9 pass; `validate_artifacts.py` exits 0.
- [ ] Works with the network disabled after setup.
- [ ] UI is usable at 375 px width and at 1440 px width; dark mode is the default; no console errors.
- [ ] No Streamlit/Gradio anywhere in the repo or dependencies.

**README must include:** project summary, architecture diagram (Section 8), the first-run sequence, measured metrics table, benchmark table, how to retrain, how to add a new dish class (update `subset_classes.json`, registry entry, rerun notebooks 01–04), troubleshooting (CUDA/CPU torch, port in use, missing artifacts, CORS), and the medical/estimate disclaimer.

---

## 15. Optional Stretch Goals (only after Section 14 is complete)
- EfficientNet-B0 comparison table in notebook 02.
- Test-time augmentation toggle (flip) in `/predict?tta=true`.
- Export history of the session's predictions to CSV (client-side only).
- Score-CAM / Grad-CAM++ selector in notebook 03 and a `method` query param.
- Dockerfile + `docker-compose.yml` (local only; not required).
