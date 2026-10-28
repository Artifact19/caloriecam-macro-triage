"""Upload validation, decoding and PNG/base64 helpers. Uploads are processed in memory only."""
from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from ..errors import AppError

# Cap decompression bombs (spec section 6.3).
Image.MAX_IMAGE_PIXELS = 50_000_000

ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MIN_SIDE_PX = 64
MAX_OUTPUT_SIDE = 512


def check_content_type(content_type: str | None) -> None:
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype not in ALLOWED_CONTENT_TYPES:
        raise AppError(
            415,
            f"Unsupported media type '{ctype or 'unknown'}'. Use JPEG, PNG or WebP.",
            "unsupported_media_type",
        )


def decode_image(data: bytes) -> np.ndarray:
    """Decode bytes -> RGB uint8 ``HxWx3`` array (EXIF orientation applied).

    Raises ``AppError(422)`` for corrupt/truncated files, bombs and images that are too small.
    """
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()  # cheap structural check; leaves the file unusable
        with Image.open(io.BytesIO(data)) as im:
            im.load()  # full decode -> catches truncated payloads
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGB")
            arr = np.asarray(im, dtype=np.uint8)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError, ValueError) as exc:
        raise AppError(422, "The file is not a valid, complete image.", "invalid_image") from exc
    h, w = arr.shape[:2]
    if min(h, w) < MIN_SIDE_PX:
        raise AppError(
            422,
            f"Image is too small ({w}x{h}); the short side must be at least {MIN_SIDE_PX}px.",
            "image_too_small",
        )
    return arr


def downscale_max_side(img: np.ndarray, max_side: int = MAX_OUTPUT_SIDE) -> np.ndarray:
    """Shrink so the longer side is <= ``max_side`` (never upscales)."""
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return img
    s = max_side / longest
    return cv2.resize(img, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)


def encode_png_base64(arr: np.ndarray) -> str:
    """Encode an RGB / RGBA uint8 array as a base64 PNG string (no data-URI prefix)."""
    mode = "RGBA" if arr.ndim == 3 and arr.shape[2] == 4 else "RGB"
    buf = io.BytesIO()
    Image.fromarray(arr, mode=mode).save(buf, format="PNG", optimize=False, compress_level=3)
    return base64.b64encode(buf.getvalue()).decode("ascii")

