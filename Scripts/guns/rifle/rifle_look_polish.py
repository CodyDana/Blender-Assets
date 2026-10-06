"""AR-01 look-polish round record (plain Python): measures what the round changed on the FINAL maps and writes
WorkFiles/guns/rifle/gates/look_polish.json (the stage-3/4 gates stay in uv_bake_paint.json / game.json).

    py -3 -B Scripts/guns/rifle/rifle_look_polish.py

- wear per handling zone (rifle_surface.METAL_WEAR on the Metal / Mag sets, rifle_paint.WOOD_WEAR on the furniture):
  bare-steel (metallic) fraction and the BC value lift of the worn band over the part's median, inside vs outside zones
- dust cover top (up-facing texels): BC value and roughness spread (P5 / P50 / P95) - the ADS slab is no longer uniform
- the receiver contact line under the cover skirt: BC value inside the 2 mm band vs the wall above / below it
- per-part BC medians (sRGB) of every finish (the round must keep them: BC gate +-12 levels, L5 per part)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "Scripts" / "guns"))
sys.path.insert(0, str(HERE))
import rifle_surface as RS  # noqa: E402
from parts import receiver_right_cover as RC  # noqa: E402
from rifle_parts import WO  # noqa: E402

W = ROOT / "WorkFiles" / "guns" / "rifle"
BAKE = W / "scratch" / "bake"
TEX = ROOT / "Exports" / "Guns" / "AR01" / "Textures"
GRIP = np.array(RS.GRIP_M, np.float32)


def load(st):
    ids = np.load(BAKE / f"{st}_ids.npy")
    pid = ids[..., 0].astype(np.int32)
    v = pid > 0
    P = np.load(BAKE / f"{st}_pos.npy")[v].astype(np.float32) * 1000.0 + GRIP
    N = np.load(BAKE / f"{st}_nrm.npy")[v].astype(np.float32) * 2.0 - 1.0
    bc = np.asarray(Image.open(TEX / f"T_AR01_{st}_BC.png").convert("RGB"))[::-1][v].astype(np.float32)
    orm = np.asarray(Image.open(TEX / f"T_AR01_{st}_ORM.png").convert("RGB"))[::-1][v].astype(np.float32) / 255.0
    return pid[v], P, N, bc, orm


def pct(a, q=(5, 50, 95)):
    return [round(float(np.percentile(a, x)), 3) for x in q] if len(a) else None


def main():
    meta = json.loads((BAKE / "bake_meta.json").read_text())
    names = {v: k for k, v in meta["parts"].items()}
    out = {"zones": {}, "medians": {}}
    for st in ("Metal", "Mag", "Furniture"):
        pid, P, N, bc, orm = load(st)
        part = np.array([names.get(int(k), "") for k in pid], object)
        val = bc.mean(1)
        for p in np.unique(part):
            s = part == p
            out["medians"][f"{st}/{p}"] = {"bc_srgb_p50": round(float(np.median(val[s])), 1),
                                           "metal_fraction": round(float((orm[s, 2] > 0.5).mean()), 4)}
        if st != "Furniture":
            for z in RS.METAL_WEAR:
                d = np.linalg.norm(P - np.array(z["center_M"], np.float32), axis=1)
                s = d < z["radius"] * 0.6
                if s.sum() < 50:
                    continue
                out["zones"][f"{st}: {z['what']}"] = {
                    "texels": int(s.sum()), "bare_fraction": round(float((orm[s, 2] > 0.5).mean()), 4),
                    "bright_fraction_vs_part_median_x1_4": round(float(np.mean(
                        val[s] > 1.4 * np.array([out['medians'][f'{st}/{p}']['bc_srgb_p50'] for p in part[s]]))), 4)}
        else:
            import rifle_paint as RP
            for p, corners in RP.WOOD_WEAR.items():
                s = part == p
                lo, hi = P[s].min(0), P[s].max(0)
                for (fx, fz, rad, w) in corners:
                    c = np.array([lo[0] + fx * (hi[0] - lo[0]), 0.0, lo[2] + fz * (hi[2] - lo[2])], np.float32)
                    c = P[s][np.argmin(np.linalg.norm((P[s] - c) * np.array([1.0, 0.25, 1.0], np.float32), axis=1))]
                    dd = np.linalg.norm((P - c) * np.array([1.0, 0.25, 1.0], np.float32), axis=1)
                    z = s & (dd < rad * 0.6)
                    med = out["medians"][f"Furniture/{p}"]["bc_srgb_p50"]
                    out["zones"][f"Furniture: {p} corner ({fx:g}, {fz:g})"] = {
                        "texels": int(z.sum()), "light_worn_fraction_x1_25": round(float(np.mean(val[z] > 1.25 * med)), 4)}
        if st == "Metal":
            c = (part == "dust_cover") & (N[:, 2] > 0.6)
            out["dust_cover_top"] = {"texels": int(c.sum()), "bc_value_p5_p50_p95": pct(val[c]),
                                     "roughness_p5_p50_p95": pct(orm[c, 1])}
            r = (part == "receiver") & (P[:, 0] > 250) & (P[:, 0] < 440) & (np.abs(P[:, 1]) > WO - 0.2)
            sb = np.array([RC.skirt_bottom(float(x)) for x in P[r, 0]], np.float32)
            dz = sb - P[r, 2]
            band, below = (dz > 0.3) & (dz < 2.0), (dz > 3.0) & (dz < 8.0)
            out["receiver_contact_line"] = {"band_bc_p50": round(float(np.median(val[r][band])), 1) if band.any() else None,
                                            "wall_below_bc_p50": round(float(np.median(val[r][below])), 1),
                                            "band_texels": int(band.sum())}
    (W / "gates" / "look_polish.json").write_text(json.dumps(out, indent=1))
    print("[look-polish] zones", len(out["zones"]), "cover top", out["dust_cover_top"], "contact",
          out["receiver_contact_line"])


if __name__ == "__main__":
    main()
