"""ONNX Runtime session wrapper (CPU)."""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import onnxruntime as ort


class OnnxEngine:
    """Thin, thread-safe wrapper (``InferenceSession.run`` is safe to call concurrently)."""

    def __init__(self, path: Path, threads: int = 0) -> None:
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        if threads and threads > 0:
            so.intra_op_num_threads = int(threads)
        self.path = Path(path)
        self.session = ort.InferenceSession(str(self.path), so, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def predict_logits(self, batch: np.ndarray) -> np.ndarray:
        """``(N, 3, 224, 224)`` float32 -> ``(N, K)`` float32 logits."""
        out = self.session.run([self.output_name], {self.input_name: np.ascontiguousarray(batch, dtype=np.float32)})
        return np.asarray(out[0], dtype=np.float32)

    def warmup(self, runs: int = 1) -> None:
        dummy = np.zeros((1, 3, 224, 224), dtype=np.float32)
        for _ in range(runs):
            self.predict_logits(dummy)

    @property
    def size_mb(self) -> float:
        return os.path.getsize(self.path) / (1024 * 1024)

