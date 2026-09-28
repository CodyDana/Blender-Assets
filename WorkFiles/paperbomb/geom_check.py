#!/usr/bin/env python
"""Headless geometry probe for props_lib.sheet: run before any bpy is involved.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python WorkFiles/paperbomb/geom_check.py
"""
import json
import math
import os
import sys

import numpy as np

PROJ = r"C:\Users\Cody\Desktop\Blender_Projects"
sys.path.insert(0, os.path.join(PROJ, "Scripts", "props"))

from props_lib import atlas as A            # noqa: E402
from props_lib import paperbomb_art as art  # noqa: E402
from props_lib import sheet as S            # noqa: E402
from props_lib.spec import PAPER_BOMB       # noqa: E402


def edge_manifold(faces):
    counts = {}
    bad_dir = 0
    for f in faces:
        n = len(f)
        for i in range(n):
            a, b = f[i], f[(i + 1) % n]
            key = (a, b) if a < b else (b, a)
            counts[key] = counts.get(key, 0) + 1
            if (a, b) in counts and a < b:
                pass
    directed = {}
    for f in faces:
        n = len(f)
        for i in range(n):
            a, b = f[i], f[(i + 1) % n]
            directed[(a, b)] = directed.get((a, b), 0) + 1
    for (a, b), c in directed.items():
        if c > 1:
            bad_dir += 1
    hist = {}
    for c in counts.values():
        hist[c] = hist.get(c, 0) + 1
    return {"edges": len(counts), "use_histogram": hist,
            "duplicated_directed_edges": bad_dir}


def main():
    spec = PAPER_BOMB
    plan = A.plan_for(spec)
    print(json.dumps(plan.describe(), indent=2))

    cfg = art.ArtConfig(ppmm=spec.ppmm, pad_mm=plan.pad_mm, supersample=1)
    outline = art.card_outline_mm(cfg)
    trim = S.Trim(outline, spec.width_mm, spec.height_mm)
    print("outline points", len(outline), "bbox",
          [round(float(x), 3) for x in (outline[:, 0].min(), outline[:, 0].max(),
                                        outline[:, 1].min(), outline[:, 1].max())])
    print("tear span", [round(x, 2) for x in trim.bite_span(spec.height_mm, spec.corner_clip_mm)])

    surface = S.Surface(
        width_mm=spec.width_mm, height_mm=spec.height_mm,
        curl_sagitta_mm=spec.curl.sagitta_mm,
        curl_deepen_sagitta_mm=spec.curl.deepen_sagitta_mm,
        curl_deepen_run_mm=spec.curl.deepen_run_mm,
        folds=tuple((f.v_mm, f.turn_deg, f.half_width_mm, f.wander_mm) for f in spec.folds),
        dog_ear=(spec.dog_ear.leg_mm, spec.dog_ear.fold_back_deg, spec.dog_ear.soften_mm),
        seed=20260919)

    out = {}
    for lod in spec.lods:
        m = S.build_sheet(spec, lod, surface, trim, plan, seed=20260919)
        co = np.array(m.verts, np.float64) * 1000.0            # back to mm
        rep = dict(m.report)
        rep["bbox_mm"] = [round(float(np.ptp(co[:, i])), 3) for i in range(3)]
        rep["z_range_mm"] = [round(float(co[:, 2].min()), 3), round(float(co[:, 2].max()), 3)]
        rep["x_range_mm"] = [round(float(co[:, 0].min()), 3), round(float(co[:, 0].max()), 3)]
        rep["y_range_mm"] = [round(float(co[:, 1].min()), 3), round(float(co[:, 1].max()), 3)]
        rep["manifold"] = edge_manifold(m.faces)
        rep["band_ok"] = lod.band[0] <= m.triangles <= lod.band[1]

        # winding: front faces must point along the analytic normal, back faces against
        good_f = good_b = bad = 0
        for gi, group in (("front", m.groups["front"]), ("back", m.groups["back"])):
            for fidx in group:
                f = m.faces[fidx]
                p = np.array([m.verts[i] for i in f], np.float64)
                nrm = np.zeros(3)
                for i in range(len(f)):
                    a, b = p[i], p[(i + 1) % len(f)]
                    nrm += np.cross(a, b)
                cu = np.mean([m.paper[i][0] for i in f])
                cv = np.mean([m.paper[i][1] for i in f])
                _, _, _, an = surface.frame(np.array([cu]), np.array([cv]))
                d = float(np.dot(nrm / (np.linalg.norm(nrm) + 1e-30), an[0]))
                if gi == "front":
                    good_f += d > 0.2
                    bad += d <= 0.2
                else:
                    good_b += d < -0.2
                    bad += d >= -0.2
        rep["winding"] = {"front_ok": good_f, "back_ok": good_b, "wrong": bad}

        # UV stretch: edge length in 3D vs in UV*ppmm
        uv = np.array([m.loop_uv[fi][k] for fi in range(len(m.faces))
                       for k in range(len(m.faces[fi]))], np.float64)
        ratios = []
        for fidx in m.groups["front"] + m.groups["back"]:
            f = m.faces[fidx]
            luv = m.loop_uv[fidx]
            for i in range(len(f)):
                a, b = f[i], f[(i + 1) % len(f)]
                d3 = np.linalg.norm(np.array(m.verts[a]) - np.array(m.verts[b])) * 1000.0
                ua, ub = luv[i], luv[(i + 1) % len(f)]
                d2 = math.hypot(ua[0] - ub[0], ua[1] - ub[1]) * plan.size / plan.ppmm
                if d3 > 0.05 and d2 > 0.05:
                    ratios.append(d3 / d2)
        ratios = np.array(ratios)
        rep["uv_stretch"] = {"min": round(float(ratios.min()), 4),
                             "max": round(float(ratios.max()), 4),
                             "p99": round(float(np.percentile(ratios, 99)), 4),
                             "mean": round(float(ratios.mean()), 4)}
        allu = np.array([p for face in m.loop_uv for p in face], np.float64)
        rep["uv_range"] = [round(float(allu.min()), 6), round(float(allu.max()), 6)]
        out[f"LOD{lod.level}"] = rep
        print(f"--- LOD{lod.level} ---")
        print(json.dumps(rep, indent=2))

    with open(os.path.join(PROJ, "WorkFiles", "paperbomb", "geom_check.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)


main()
