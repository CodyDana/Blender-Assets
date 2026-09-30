"""Round 5 fix f1 (2026-09-29): T_DJS_SunsetSky, our own painted BACKLIT SUNSET SKY (plain Python + numpy).

Why (both round-5 Unreal judges' first blocker): the r5 sky was the SkyAtmosphere seen through a translucent painted
cloud layer (make_sky_clouds.py): a grey-blue / lavender field with smeared, posterised pink cloud texture and no warm
horizon glow, the sun off to the west. dojo1_reference2 is backlit: the brightest warm orange band sits on the horizon
behind the hall (left of centre), the sky rises through peach to a dusty violet, and banks of small cumulus /
altocumulus are lit from below (peach-orange undersides, lavender-grey tops). So the dome is now a FULL, OPAQUE sky
(alpha 1 everywhere; the SkyAtmosphere stays for the sun's transmittance, aerial perspective and the real-time sky light).

Nothing is copied from the reference: the gradient is an analytic function of the elevation and the angle to the sun
(the layout sun, look_r3.ENV), the colours are the reference's MEASURED values (sRGB medians of dojo1_reference2:
horizon toward the glow (249, 186, 130), horizon away from it (160, 135, 140), upper sky (110-145, 102-130, 122-146),
lit cloud undersides (238, 185, 150)), and the clouds are our own band-limited noise projected onto a flat cloud deck
(so they shrink and bunch into bands toward the horizon, as real clouds do). Anti-aliased by construction: every noise
octave fades out where its wavelength falls under 3 texels of its projected footprint.

Map (dj_sc_level.sky_dome material): u = atan2(y, x) / 2 pi + 0.5 (UE frame), v = 1 - asin(z) / (pi / 2)
(v 0 = zenith, 1 = horizon; directions below the horizon clamp to the horizon row). 8192 x 2048 = 22.8 texels / deg,
about 1:1 with the 1920-wide captures (the r3/r5 4096 x 1024 layer was magnified 2.4x: soft and blotchy).

CALIBRATION: the dome is unlit emissive (texture x Intensity) and goes through the tonemapper, so a painted value is not
the value the capture shows. `--calib <json>` reads a per-channel table measured on a capture of the previous painting
(fit_sky_calib.py: desired output sRGB -> painted linear), so the painting targets the OUTPUT colours below.

Run: py -3 Scripts/dojo/showcase/make_sky_sunset.py [--calib <json>]
Out: Exports/DojoKit/Showcase/Textures/T_DJS_SunsetSky.png (8192 x 2048 RGB8, sRGB)
     WorkFiles/dojo/build/unreal/round5/f1_work/sky_sunset.json (+ sky_sunset_target.npy: the desired output sRGB)
"""
import json
import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import look_r3  # noqa: E402

OUT = ROOT / "Exports" / "DojoKit" / "Showcase" / "Textures" / "T_DJS_SunsetSky.png"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "unreal" / "round5" / "f1_work"
REP = WORK / "sky_sunset.json"
W, H = 8192, 2048
P = look_r3.ENV.get("sky_dome", {})
SEED = int(P.get("seed", 11))
ARGS = sys.argv[1:]
CALIB = Path(ARGS[ARGS.index("--calib") + 1]) if "--calib" in ARGS else None
TEXEL_RAD = math.radians(90.0 / H)
INTENSITY_MULT = [1.0]   # the calibrated painting's scale: multiply the dome Intensity (the calibration's) by it

# ---- desired OUTPUT colours (sRGB 0-255), measured on dojo1_reference2 (see the docstring)
SKY_SUN = [(0.0, (252, 168, 98)), (3.0, (250, 176, 112)), (7.0, (243, 180, 128)), (13.0, (226, 172, 140)),
           (22.0, (196, 160, 152)), (35.0, (156, 138, 152)), (55.0, (122, 116, 142)), (90.0, (104, 104, 134))]
SKY_ANTI = [(0.0, (168, 142, 146)), (4.0, (160, 138, 146)), (10.0, (146, 130, 146)), (20.0, (128, 118, 140)),
            (35.0, (112, 108, 134)), (60.0, (100, 100, 130)), (90.0, (96, 98, 130))]
GLOW = (255, 214, 158)             # circumsolar core
CLOUD_LIT_SUN = (250, 190, 140)     # undersides / rims toward the glow
CLOUD_LIT_MID = (236, 176, 150)
CLOUD_LIT_FAR = (196, 160, 160)
CLOUD_SHADE_HI = (136, 118, 136)    # shaded cloud bodies high in the sky
CLOUD_SHADE_LO = (160, 132, 138)    # shaded bodies near the horizon (lifted by the haze)


def srgb_to_lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def write_png(path, rgb8):
    h, w, ch = rgb8.shape
    raw = b"".join(b"\x00" + rgb8[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def ramp(table, x):
    """Piecewise-linear colour ramp (in LINEAR light) over x (degrees)."""
    xs = np.array([t[0] for t in table])
    cs = srgb_to_lin([t[1] for t in table])
    return np.stack([np.interp(x, xs, cs[:, i]) for i in range(3)], -1)


def band_tile(rng, n=512, f0=9.0, f1=42.0):
    """A periodic n x n tile of band-limited noise (frequencies f0..f1 cycles / tile), unit variance."""
    F = np.fft.fft2(rng.standard_normal((n, n)))
    f = np.sqrt(np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2) * n
    F[(f < f0) | (f > f1)] = 0
    F = F * np.where(f > 0, (21.0 / np.maximum(f, 1e-6)) ** 0.5, 0)   # a broad band, 1/f-weighted (no ripples)
    t = np.real(np.fft.ifft2(F))
    return ((t - t.mean()) / t.std()).astype(np.float32)


def sample(tile, x, y):
    """Bilinear, wrapping; x, y in tile texels."""
    n = tile.shape[0]
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx, fy = (x - x0).astype(np.float32), (y - y0).astype(np.float32)
    x0 %= n
    y0 %= n
    x1, y1 = (x0 + 1) % n, (y0 + 1) % n
    a = tile[y0, x0] * (1 - fx) + tile[y0, x1] * fx
    b = tile[y1, x0] * (1 - fx) + tile[y1, x1] * fx
    return a * (1 - fy) + b * fy


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    e_s, a_s = math.radians(look_r3.ENV["sun_elev_deg"]), math.radians(look_r3.ENV["sun_azimuth_deg_from_x"])
    sun_ue = np.array([math.cos(e_s) * math.cos(a_s), -math.cos(e_s) * math.sin(a_s), math.sin(e_s)])
    sun_az_ue = math.atan2(sun_ue[1], sun_ue[0])
    u = (np.arange(W, dtype=np.float64) + 0.5) / W
    v = (np.arange(H, dtype=np.float64) + 0.5) / H
    az = (u - 0.5) * 2 * math.pi                                   # UE azimuth per column
    el = (1.0 - v) * math.pi / 2                                   # elevation per row
    eld = np.degrees(el)
    AZ, EL = np.meshgrid(az, el)
    ELD = np.degrees(EL)
    d = np.stack([np.cos(EL) * np.cos(AZ), np.cos(EL) * np.sin(AZ), np.sin(EL)], -1)
    gam = np.degrees(np.arccos(np.clip(d @ sun_ue, -1, 1)))       # angle to the sun
    daz = np.degrees(np.abs(np.angle(np.exp(1j * (AZ - sun_az_ue)))))   # azimuth difference to the sun
    del d
    # ---- clear sky: the sun-side and anti-sun ramps by elevation, blended by the azimuth to the sun; the horizon band
    #      toward the sun is wide (reference 2: warm from the left edge to past the centre)
    ws = np.exp(-(daz / 62.0) ** 2)[..., None] * (0.15 + 0.85 * np.exp(-np.clip(ELD - 4.0, 0, None) / 14.0))[..., None]
    sky = ramp(SKY_ANTI, ELD) * (1 - ws) + ramp(SKY_SUN, ELD) * ws
    core = (0.85 * np.exp(-gam / 5.0) + 0.35 * np.exp(-gam / 18.0))[..., None]
    sky = sky * (1 - np.clip(core, 0, 1)) + srgb_to_lin(GLOW) * np.clip(core, 0, 1)
    # ---- the cloud deck: plane coordinates (units of the deck height) of each direction; anisotropic (banks stretched
    #      across the view to the sun), octaves faded under their projected texel footprint
    tel = np.maximum(np.tan(EL), math.tan(math.radians(0.4)))
    r = 1.0 / tel                                                  # horizontal distance to the deck
    px, py = r * np.cos(AZ - sun_az_ue), r * np.sin(AZ - sun_az_ue)   # x toward the sun
    foot = (1.0 / np.sin(np.maximum(EL, math.radians(0.4))) ** 2) * TEXEL_RAD   # radial footprint per texel
    rng = np.random.default_rng(SEED)
    lam0, n_oct, rough = 2.2, 7, 0.62
    dens = np.zeros_like(r, dtype=np.float32)
    var = np.zeros_like(r, dtype=np.float32)
    for k in range(n_oct):
        lam = lam0 / 2.0 ** k
        amp = rough ** k
        tile = band_tile(rng)
        wv = smoothstep(3.0, 6.0, lam / foot).astype(np.float32)   # fade when lam < 3-6 footprints
        s = 512 / (21.0 * lam)                                     # tile texels per deck unit (21 wavelengths / tile)
        rot = rng.uniform(0, 2 * math.pi)
        ca, sa = math.cos(rot), math.sin(rot)
        qx = (px * ca - py * sa) * s * 0.62 + 97.0 * k            # stretch x (toward the sun) by 1 / 0.62
        qy = (px * sa + py * ca) * s
        dens += (amp * wv) * sample(tile, qx, qy)
        var += (amp * wv) ** 2
    dens = dens / np.sqrt(np.maximum(var, 1e-6))                   # unit variance (kept where octaves faded)
    # coverage by elevation: a clear warm band on the horizon, banks above it, thinner toward the zenith
    cov = 0.10 + 0.40 * smoothstep(2.0, 9.0, ELD) - 0.05 * smoothstep(40.0, 80.0, ELD)
    cov += 0.10 * smoothstep(2.0, 9.0, ELD) * np.exp(-(daz / 90.0) ** 2)   # more cloud toward the glow (ref 2)
    thr = np.quantile(dens[::8, ::8], 1.0 - 0.34) + (0.34 - cov) * 1.6
    thick = dens - thr
    alpha = smoothstep(0.0, 0.22, thick) * smoothstep(1.2, 4.5, ELD)
    # lighting: undersides / rims toward the sun (the density falls toward the horizon and toward the sun), thin parts
    # glow near the sun (forward scatter), thick cores keep their own shade
    step = np.maximum(0.05, 3.0 * foot)                            # deck units (never under 3 texels)
    rx, ry = px / np.maximum(r, 1e-6), py / np.maximum(r, 1e-6)    # outward (toward the horizon) direction
    base = np.zeros_like(dens)
    acc_o = np.zeros_like(dens)
    acc_s = np.zeros_like(dens)
    rng = np.random.default_rng(SEED)                              # the same tiles and rotations as above
    for k in range(n_oct):
        lam = lam0 / 2.0 ** k
        amp = rough ** k
        tile = band_tile(rng)
        wv = smoothstep(3.0, 6.0, lam / foot).astype(np.float32)
        s = 512 / (21.0 * lam)
        rot = rng.uniform(0, 2 * math.pi)
        ca, sa = math.cos(rot), math.sin(rot)
        for acc, ox, oy in ((base, 0.0, 0.0), (acc_o, rx * step, ry * step), (acc_s, step, 0.0 * step)):
            X, Y = px + ox, py + oy
            qx = (X * ca - Y * sa) * s * 0.62 + 97.0 * k
            qy = (X * sa + Y * ca) * s
            acc += (amp * wv) * sample(tile, qx, qy)
    sd = np.sqrt(np.maximum(var, 1e-6))
    lit_out = np.clip((base - acc_o) / sd * 2.2, -1, 1)          # density drops toward the horizon: underside lit
    lit_sun = np.clip((base - acc_s) / sd * 2.2, -1, 1)          # drops toward the sun: sun-facing rim lit
    del acc_o, acc_s, base
    glow = np.exp(-gam / 38.0)
    lit = np.clip(0.60 + 0.32 * lit_out + 0.25 * lit_sun * glow + 0.2 * glow - 0.32 * smoothstep(0.3, 1.3, thick), 0, 1)
    lit = np.clip(lit + 0.35 * (1 - smoothstep(0.0, 0.18, thick)) * glow, 0, 1)   # thin edges glow toward the sun
    g2 = np.exp(-gam / 70.0)[..., None]
    lit_col = (srgb_to_lin(CLOUD_LIT_SUN) * np.exp(-gam / 30.0)[..., None]
               + srgb_to_lin(CLOUD_LIT_MID) * (g2 - np.exp(-gam / 30.0)[..., None]).clip(0, 1)
               + srgb_to_lin(CLOUD_LIT_FAR) * (1 - g2))
    shade_col = srgb_to_lin(CLOUD_SHADE_LO) * smoothstep(25.0, 3.0, ELD)[..., None] + \
        srgb_to_lin(CLOUD_SHADE_HI) * (1 - smoothstep(25.0, 3.0, ELD))[..., None]
    cloud = shade_col * (1 - lit[..., None]) + lit_col * lit[..., None]
    # clouds near the horizon sink into the haze (aerial perspective toward the sky colour)
    haze = smoothstep(14.0, 1.5, ELD)[..., None] * 0.45
    cloud = cloud * (1 - haze) + sky * haze
    col = sky * (1 - alpha[..., None]) + cloud * alpha[..., None]
    target_srgb = lin_to_srgb(col)                                 # the desired OUTPUT colour (0..1)
    # ---- calibration: desired output sRGB -> painted linear (per channel), measured on the previous capture
    if CALIB is not None:
        cal = json.loads(CALIB.read_text(encoding="utf-8"))
        paint = np.stack([np.interp(target_srgb[..., i] * 255.0, cal["out"][i], cal["paint_lin"][i])
                          for i in range(3)], -1)
        scale = max(1.0, float(np.quantile(paint.max(-1)[::4, ::4], 0.999)))   # > 1: raise the dome Intensity instead
        paint_srgb = lin_to_srgb(paint / scale)
        INTENSITY_MULT[0] = scale
    else:
        paint_srgb = target_srgb
    rng = np.random.default_rng(SEED + 99)
    x = paint_srgb * 255.0 + rng.random(paint_srgb.shape) - rng.random(paint_srgb.shape)   # +-1 LSB dither
    rgb8 = np.clip(np.round(x), 0, 255).astype(np.uint8)
    write_png(OUT, rgb8)
    WORK.mkdir(parents=True, exist_ok=True)
    np.save(WORK / "sky_sunset_target.npy", (target_srgb[::4, ::4] * 255).astype(np.float32))
    sun_u = sun_az_ue / (2 * math.pi) + 0.5
    rep = {"out": str(OUT), "size": [W, H], "seed": SEED, "sun_ue": sun_ue.round(4).tolist(), "sun_u": round(sun_u, 4),
           "sun_elev_deg": look_r3.ENV["sun_elev_deg"], "sun_az_deg_from_x": look_r3.ENV["sun_azimuth_deg_from_x"],
           "calib": str(CALIB) if CALIB else None, "intensity_mult": round(INTENSITY_MULT[0], 4), "cloud_cover": round(float((alpha > 0.5).mean()), 3),
           "target_horizon_sun_srgb": [int(t) for t in (target_srgb[H - 20, int(sun_u * W) % W] * 255)],
           "target_zenith_srgb": [int(t) for t in (target_srgb[5, 0] * 255)]}
    REP.write_text(json.dumps(rep, indent=1))
    print("SKY_SUNSET", json.dumps(rep))


main()
