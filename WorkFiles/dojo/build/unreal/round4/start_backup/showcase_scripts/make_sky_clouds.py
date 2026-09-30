"""Round 3 fix f1 (2026-09-28): T_DJS_SunsetClouds, our own procedural sunset cloud layer (plain Python + numpy).

Why: the whole-courtyard judge's first blocker is the sky (reference 2: a warm golden-hour sky with orange-lit cloud
banks between blue-violet gaps; the captures had a flat gradient). UE 5.8's VolumetricCloud does not render in the
showcase's SceneCapture2D stills (tested at coverage 0.9 with the Cloud show flag and r.VolumetricRenderTarget 0: no
cloud), so the clouds are a painted layer: an equirectangular RGBA map (u = azimuth, v = 0 zenith .. 1 horizon) on the
engine's SM_SkySphere as an unlit, translucent dome (dj_sc_level.sky_dome); the SkyAtmosphere shows through the gaps.

Nothing is copied from the reference: the clouds are periodic FFT noise (fractal, stretched along the azimuth into
flat altocumulus banks), the colour is a function of the angle to the sun (the layout sun, UE frame): lit peach-orange
undersides toward the sun, grey-violet away from it, brighter rims. Colour targets are the reference's measured cloud
and sky values (dojo1_reference2: lit clouds sRGB (213, 173, 154), sky low (221, 162, 134), sky top (175, 157, 160)).

Run: py -3 Scripts/dojo/showcase/make_sky_clouds.py
Out: Exports/DojoKit/Showcase/Textures/T_DJS_SunsetClouds.png (4096 x 1024 RGBA8, sRGB colour, linear alpha)
     WorkFiles/dojo/build/unreal/round3/f1_work/sky_clouds.json
"""
import json
import math
import sys
import zlib
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import look_r3  # noqa: E402

OUT = ROOT / "Exports" / "DojoKit" / "Showcase" / "Textures" / "T_DJS_SunsetClouds.png"
REP = ROOT / "WorkFiles" / "dojo" / "build" / "unreal" / "round3" / "f1_work" / "sky_clouds.json"
W, H = 4096, 1024
P = look_r3.ENV.get("sky_dome", {})
SEED = int(P.get("seed", 7))
COVER = float(P.get("coverage", 0.46))


def write_png(path, rgba):
    a = np.clip(np.round(rgba * 255.0), 0, 255).astype(np.uint8)
    h, w, ch = a.shape
    raw = b"".join(b"\x00" + a[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def fbm(seed, beta, su, sv, fmin=3.0):
    """Periodic 1/f^beta noise (periodic in u; v is padded x2 and cropped, so no wrap between zenith and horizon)."""
    rng = np.random.default_rng(seed)
    h2 = H * 2
    F = np.fft.fft2(rng.standard_normal((h2, W)))
    fv = np.fft.fftfreq(h2)[:, None] * h2 / sv
    fu = np.fft.fftfreq(W)[None, :] * W / su
    f = np.sqrt(fu * fu + fv * fv)
    f[0, 0] = 1.0
    F = F / f ** beta
    F[f < fmin] = 0            # no sky-sized blobs: cloud banks, not one lit patch
    n = np.real(np.fft.ifft2(F))[:H]
    return (n - n.mean()) / n.std()


def srgb_to_lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def main():
    e, a = math.radians(look_r3.ENV["sun_elev_deg"]), math.radians(look_r3.ENV["sun_azimuth_deg_from_x"])
    sun_ue = np.array([math.cos(e) * math.cos(a), -math.cos(e) * math.sin(a), math.sin(e)])   # Blender -> UE (y flip)
    u = (np.arange(W) + 0.5) / W
    v = (np.arange(H) + 0.5) / H
    U, V = np.meshgrid(u, v)
    az = (U - 0.5) * 2 * math.pi                       # material: u = atan2(y, x) / 2 pi + 0.5
    el = (1.0 - V) * math.pi / 2                       # v 0 = zenith, 1 = horizon
    d = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], -1)
    cosg = np.clip(d @ sun_ue, -1, 1)
    gam = np.degrees(np.arccos(cosg))                  # angle to the sun
    # cloud field: flat banks (stretched 5x along the azimuth), fractal edges; more cloud at mid elevations
    base = 0.65 * fbm(SEED, 1.5, 1.0 / 5.0, 1.0, 6.0) + 0.35 * fbm(SEED + 1, 1.2, 1.0 / 2.5, 1.0, 12.0)
    detail = fbm(SEED + 2, 1.0, 1.0 / 2.0, 1.0, 40.0)
    eld = np.degrees(el)
    band = np.clip((eld - 2.0) / 8.0, 0, 1) * (1.0 - 0.55 * np.clip((eld - 35.0) / 45.0, 0, 1))
    thr = np.quantile(base, 1.0 - COVER)
    dens = np.clip((base - thr) * 1.1 + 0.08 * detail, 0, 1) * band
    alpha = np.clip(dens ** 0.8 * 1.5, 0, 0.95)
    # colour: toward the sun lit peach-orange (the reference's lit cloud), away from it grey-violet; thin edges brighter
    lit = srgb_to_lin((244, 166, 116))
    far = srgb_to_lin((138, 118, 142))
    glow = np.exp(-gam / 55.0)[..., None]
    col = far * (1 - glow) + lit * glow
    rim = (1.0 + 0.35 * np.clip(1.0 - dens * 2.2, 0, 1) * np.exp(-gam / 40.0))[..., None]
    core = (1.0 - 0.28 * np.clip(dens - 0.35, 0, 1) / 0.65)[..., None]   # thick cores darker (their own shadow)
    under = (1.0 + 0.25 * np.clip(0.3 - V, -0.3, 0.3))[..., None]       # nothing below the horizon
    col = col * rim * core * under
    rgba = np.concatenate([lin_to_srgb(col), alpha[..., None]], -1)
    write_png(OUT, rgba)
    rep = {"out": str(OUT), "size": [W, H], "coverage": COVER, "seed": SEED, "sun_ue": sun_ue.round(4).tolist(),
           "sun_u": round(float(math.atan2(sun_ue[1], sun_ue[0]) / (2 * math.pi) + 0.5), 4),
           "alpha_mean": round(float(alpha.mean()), 3), "alpha_frac_gt_0.3": round(float((alpha > 0.3).mean()), 3),
           "colour_lit_srgb": [244, 166, 116], "colour_far_srgb": [138, 118, 142]}
    REP.parent.mkdir(parents=True, exist_ok=True)
    REP.write_text(json.dumps(rep, indent=1))
    print("SKY_CLOUDS", json.dumps(rep))


main()
