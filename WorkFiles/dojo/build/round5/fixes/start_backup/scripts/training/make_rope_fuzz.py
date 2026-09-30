"""Kit 9 r2 (2026-09-28, prop material pass): the makiwara rope's fibre fuzz, layered ON the shared library rope.

The judges asked for a lighter makiwara rope mesh (fewer sides and steps) with the straw's fibre fuzz carried by the
material instead of the geometry. This script loads the SHARED LIBRARY set T_DJ_Rope_{BC,N,ORM}
(Exports/DojoKit/Materials/Textures, read only; U = 4 lays along the rope, V = once round it) and adds, seamlessly
(every stamp wraps), a layer of stray straw fibres:
  - thin light fibres (1 px, 1.5-6 mm long) mostly along the strands (+-35 deg) with a few random strays, some
    crossing the strand grooves;
  - a soft halo round them (the fuzzy sheen of loose fibres), which also half-fills the dark strand grooves;
  - a softer strand relief in the normal map (fuzz hides the hard lay), rougher and less occluded where fibres are.
The library set itself is untouched. Output: Exports/DojoKit/Props/training/Textures/T_DKP_Train_RopeFuzz_{BC,N,ORM}.png
(the material M_DKP_Train_RopeFuzz is built on the library's node graph by build_training_props.py; in Unreal an MI of
M_DJ_Lib_Opaque, UseWear off, exactly like MI_DJ_Rope with these three maps).

Run: py -3 Scripts/dojo/props/training/make_rope_fuzz.py
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
LIB = ROOT / "Exports" / "DojoKit" / "Materials" / "Textures"
OUT = ROOT / "Exports" / "DojoKit" / "Props" / "training" / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "training"


def load(name):
    return np.asarray(Image.open(LIB / f"T_DJ_Rope_{name}.png").convert("RGB")).astype(np.float64) / 255.0


def save(arr, name):
    Image.fromarray(np.clip(np.round(arr * 255), 0, 255).astype(np.uint8), "RGB").save(OUT / f"T_DKP_Train_RopeFuzz_{name}.png")


def blur(a, s):
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (np.pi * s) ** 2 * (fx * fx + fy * fy))))


def fibres(h, w, rng, count, len_px, ang0, ang_sd, curl):
    m = np.zeros((h, w))
    for _ in range(count):
        L = int(rng.uniform(*len_px))
        a = ang0 + rng.normal(0, ang_sd)
        k = rng.normal(0, curl)
        t = np.arange(L, dtype=np.float64)
        ang = a + k * t
        x = rng.uniform(0, w) + np.cumsum(np.cos(ang))
        y = rng.uniform(0, h) + np.cumsum(np.sin(ang))
        amp = rng.uniform(0.45, 1.0) * np.sin(np.pi * (t + 0.5) / L) ** 0.4
        xi, yi = np.round(x).astype(int) % w, np.round(y).astype(int) % h
        m[yi, xi] = np.maximum(m[yi, xi], amp)
    return m


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bc, nrm, orm = load("BC"), load("N"), load("ORM")
    h, w = bc.shape[:2]                      # 512 x 1024: rows = V (round the rope), columns = U (along it)
    rng = np.random.default_rng(1633)
    # strand lines 3 v + 12 u = const run along (du, dv) = (1, -4) tiles = (1024, -2048) px; image rows go down (-V)
    strand = np.arctan2(2048.0, 1024.0)
    # r3: more stray fibres and a stronger halo (judge r2: "the sheet's rope looks hairier")
    f = np.maximum(fibres(h, w, rng, 4200, (8, 34), strand, 0.65, 0.05),
                   0.8 * fibres(h, w, rng, 1300, (6, 24), 0.0, 1.6, 0.08))
    f = np.maximum(f, 0.6 * blur(f, 0.5))
    halo = np.clip(blur(f, 3.0) * 4.0, 0, 1)
    groove = np.clip(1.0 - orm[..., 0], 0, 1)          # the library AO is low in the strand grooves
    fib_c = np.array([214, 190, 140]) / 255.0
    fuzz_c = np.array([190, 160, 112]) / 255.0
    out = bc * (1 - 0.55 * f[..., None]) + fib_c * 0.55 * f[..., None]
    t = (0.22 * halo + 0.26 * halo * groove)[..., None]
    out = out * (1 - t) + fuzz_c * t
    n = nrm * 0.75 + np.array([0.5, 0.5, 1.0]) * 0.25    # softer lay under the fuzz
    n[..., :2] = n[..., :2] * (1 - 0.5 * f[..., None]) + 0.5 * 0.5 * f[..., None]
    o = orm.copy()
    o[..., 0] = o[..., 0] + (1 - o[..., 0]) * (0.25 + 0.35 * halo)
    o[..., 1] = np.clip(o[..., 1] + 0.05 * halo, 0, 1)
    o[..., 2] = 0.0
    save(out, "BC")
    save(np.clip(n, 0, 1), "N")
    save(o, "ORM")
    lum = lambda a: 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]  # noqa: E731
    rep = {"source": "library T_DJ_Rope_{BC,N,ORM} (read only) + fibre fuzz layer", "size_px": [w, h],
           "fibre_cover_frac": round(float((f > 0.3).mean()), 4), "halo_mean": round(float(halo.mean()), 3),
           "median_srgb_library": [int(x) for x in np.round(np.median(bc.reshape(-1, 3), 0) * 255)],
           "median_srgb_fuzz": [int(x) for x in np.round(np.median(out.reshape(-1, 3), 0) * 255)],
           "groove_lum_p10_library_vs_fuzz": [round(float(np.percentile(lum(bc), 10)) * 255, 1),
                                               round(float(np.percentile(lum(out), 10)) * 255, 1)],
           "seam_wrap_step_vs_interior": round(float(np.abs(out[:, 0] - out[:, -1]).mean() /
                                                   (np.abs(np.diff(out, axis=1)).mean() + 1e-9)), 3)}
    rp = WORK / "textures_report.json"
    old = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    old["RopeFuzz_r3"] = rep
    rp.write_text(json.dumps(old, indent=1), encoding="utf-8")
    print("ROPEFUZZ", json.dumps(rep))


if __name__ == "__main__":
    main()
