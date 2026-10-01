"""Investigation overlay preview (G20.1+).

The INVESTIGATE spatial viewer can only use a PNG/JPEG URL as its image
background — GeoTIFF inputs never qualify, so multi-image investigations fell
back to bare SVG polygons on a dark grid. This module burns a real preview:

    post-event optical (T2) + red change-mask tint + blue grounding box
    -> ``overlay.png`` served via ``GET /artifact``.

Everything rendered comes from executed specialist outputs (the change mask
PNG, the grounding box). Nothing is invented: no mask/box -> no overlay.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np


def _to_rgb(arr: np.ndarray) -> np.ndarray:
    """(bands, H, W) of any dtype -> (H, W, 3) uint8 via per-band min-max."""
    bands = arr.shape[0]
    picks = [0, 1, 2] if bands >= 3 else [0] * 3
    rgb = np.stack([arr[i] for i in picks], axis=-1).astype(np.float64)
    out = np.zeros_like(rgb)
    for c in range(3):
        ch = rgb[..., c]
        lo, hi = float(ch.min()), float(ch.max())
        out[..., c] = 0.0 if hi <= lo else (ch - lo) / (hi - lo) * 255.0
    return out.astype(np.uint8)


def build_investigation_overlay(
    t2_path: str | Path,
    mask_path: str | Path | None,
    ground_box_xyxy: list[float] | None,
    ground_dims_wh: list[int] | None,
    out_path: str | Path,
    max_side: int = 1024,
) -> str | None:
    """Render the overlay PNG. Returns ``str(out_path)`` or ``None``."""
    try:
        import rasterio  # noqa: PLC0415
        from PIL import Image, ImageDraw  # noqa: PLC0415

        with rasterio.open(t2_path) as d:
            base = _to_rgb(d.read())
        h, w = base.shape[:2]
        scale = min(1.0, max_side / max(h, w))
        if scale < 1.0:
            nw, nh = int(w * scale), int(h * scale)
            base = np.asarray(Image.fromarray(base).resize((nw, nh), Image.BILINEAR))
            h, w = nh, nw
        img = Image.fromarray(base).convert("RGB")

        if mask_path and Path(mask_path).exists():
            m = np.asarray(Image.open(mask_path).convert("L").resize((w, h)))
            tint = Image.new("RGB", (w, h), (255, 70, 60))
            img.paste(Image.blend(img, tint, 0.45), (0, 0), Image.fromarray((m > 127).astype(np.uint8) * 255))

        if ground_box_xyxy and len(ground_box_xyxy) == 4 and ground_dims_wh:
            gw, gh = ground_dims_wh
            if gw > 0 and gh > 0:
                sx, sy = w / gw, h / gh
                x0, y0, x1, y1 = (ground_box_xyxy[0] * sx, ground_box_xyxy[1] * sy,
                                  ground_box_xyxy[2] * sx, ground_box_xyxy[3] * sy)
                draw = ImageDraw.Draw(img)
                for off in range(3):
                    draw.rectangle([x0 - off, y0 - off, x1 + off, y1 + off], outline=(79, 157, 255))

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "PNG")
        return str(out_path)
    except Exception:  # noqa: BLE001 - overlay is best-effort; the result stands without it
        return None
