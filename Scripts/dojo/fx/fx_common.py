"""Shared constants and numpy helpers for the DojoFX build (plain Python 3 AND Blender's Python; no bpy here).

Paths, names, the petal UV frame, colour conversions, periodic fBm noise and PNG writing (PIL when available,
else the caller passes its own writer).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
REF_DIR = ROOT / "References/Dojo"
PETAL_REF = REF_DIR / "dojo_petals_ref.png"
MIST_REF = REF_DIR / "dojo_mist_ref.png"
WORK = ROOT / "WorkFiles/dojo/build/fx"
EXPORT = ROOT / "Exports/DojoKit/FX"
TEX = EXPORT / "Textures"
BLEND = ROOT / "Assets/Dojo/DojoFX.blend"
SRC_TEX = ROOT / "WorkFiles/dojo/build/fx/src_textures"  # large intermediate renders (not shipped)
BLENDER = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
LOCK_ASSET = "DojoFX"

# Petal UV frame: petal space y = 0 (base) .. 1 (top of the lobes), x in units of the length, centred.
UV_SCALE = 0.94
UV_MARGIN = 0.03


def petal_to_uv(x, y):
    return 0.5 + np.asarray(x) * UV_SCALE, UV_MARGIN + np.asarray(y) * UV_SCALE


def uv_to_petal(u, v):
    return (np.asarray(u) - 0.5) / UV_SCALE, (np.asarray(v) - UV_MARGIN) / UV_SCALE


def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float64), 0.0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def periodic_noise(size: int, freq: float, seed: int, aniso=(1.0, 1.0)) -> np.ndarray:
    """Tileable band-limited noise (FFT-filtered white noise), zero mean, unit std. freq in cycles per tile."""
    rng = np.random.default_rng(seed)
    white = rng.standard_normal((size, size))
    fy = np.fft.fftfreq(size)[:, None] * size / aniso[1]
    fx = np.fft.fftfreq(size)[None, :] * size / aniso[0]
    f = np.sqrt(fx * fx + fy * fy)
    band = np.exp(-((f - freq) ** 2) / (2 * (0.5 * freq) ** 2)) * (f > 0)
    out = np.real(np.fft.ifft2(np.fft.fft2(white) * band))
    out -= out.mean()
    return out / (out.std() + 1e-9)


def fbm(size: int, base_freq: float, octaves: int, seed: int, gain=0.5, aniso=(1.0, 1.0)) -> np.ndarray:
    acc = np.zeros((size, size))
    amp, total = 1.0, 0.0
    for o in range(octaves):
        acc += amp * periodic_noise(size, base_freq * 2 ** o, seed + 101 * o, aniso)
        total += amp
        amp *= gain
    return acc / total


def height_to_normal_dx(h: np.ndarray, strength: float) -> np.ndarray:
    """Height (rows top->bottom = v high->low, v up) to a DirectX tangent normal in 0-1 (G = -Y of OpenGL)."""
    size = h.shape[0]
    dhdu = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * size
    dhdrow = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * size
    dhdv = -dhdrow
    nx = -dhdu * strength
    ny_gl = -dhdv * strength
    nz = np.ones_like(h)
    n = np.stack([nx, ny_gl, nz], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    n[..., 1] *= -1.0  # DirectX
    return n * 0.5 + 0.5


def save_png(arr: np.ndarray, path: Path, mode: str | None = None) -> str:
    """Save a float 0-1 array (h,w) / (h,w,3) / (h,w,4) as an 8-bit PNG with PIL."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    a = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    try:
        from PIL import Image
    except ImportError:  # Blender's Python: write with the bundled OpenImageIO
        import OpenImageIO as oiio
        a3 = a if a.ndim == 3 else a[..., None]
        spec = oiio.ImageSpec(a3.shape[1], a3.shape[0], a3.shape[2], oiio.UINT8)
        o = oiio.ImageOutput.create(str(path))
        o.open(str(path), spec)
        o.write_image(np.ascontiguousarray(a3))
        o.close()
        return str(path)
    if a.ndim == 2:
        img = Image.fromarray(a, "L")
    elif a.shape[2] == 3:
        img = Image.fromarray(a, "RGB")
    else:
        img = Image.fromarray(a, "RGBA")
    img.save(str(path), optimize=True)
    return str(path)


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=1), encoding="utf-8")


def dilate_rgb(rgb: np.ndarray, alpha: np.ndarray, iters: int = 24) -> np.ndarray:
    """Push colours outward from alpha>0.5 into the transparent area (avoids dark mip fringes)."""
    rgb = rgb.copy()
    known = alpha > 0.5
    for _ in range(iters):
        if known.all():
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros(alpha.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = np.roll(known, (dy, dx), axis=(0, 1))
            acc += np.roll(rgb, (dy, dx), axis=(0, 1)) * k[..., None]
            cnt += k
        grow = (~known) & (cnt > 0)
        rgb[grow] = acc[grow] / cnt[grow][:, None]
        known = known | grow
    rgb[~known] = rgb[known].mean(axis=0) if known.any() else 0.5
    return rgb
