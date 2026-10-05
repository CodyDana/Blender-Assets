"""Front-sight detail builder's private harness (detail pass round 1). Lets this part iterate while the other part
builders run in parallel: it never writes Assets/Guns/AR01.blend or scratch/form_tris.npz.

    py -3 -B Scripts/guns/rifle/parts/front_sight_dev.py build            rebuild only this module's objects into a
                                                                           copy of the baseline blend
    py -3 -B Scripts/guns/rifle/parts/front_sight_dev.py crop  --tag r1i1 ROUGH LOOK crops at the solved c3 / q34
                                                                           cameras (fixed from the setup) + numbers
    py -3 -B Scripts/guns/rifle/parts/front_sight_dev.py l2    [--tag x]  per-part L2 (side view) on the private npz
    py -3 -B Scripts/guns/rifle/parts/front_sight_dev.py contacts         G5 static intersections / gaps of this part

Private scratch: WorkFiles/guns/rifle/scratch/detail/front_sight/ (base.blend + base_tris.npz = the baseline form
build copied at the start of the round; fs.blend + fs_tris.npz = baseline with this module rebuilt; cameras/ =
copies of the setup's solved cameras, kept fixed so the comparison is not re-fitted to our own changes).
Review output: WorkFiles/guns/rifle/review/detail/front_sight/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent            # Scripts/guns/rifle/parts
RIFLE = HERE.parent
sys.path.insert(0, str(RIFLE))

try:
    import bpy  # noqa: F401
    IN_BLENDER = True
except ImportError:
    IN_BLENDER = False

from rifle_common import SCRATCH, REVIEW, GRIP, SHEET  # noqa: E402

PRIV = SCRATCH / "detail" / "front_sight"
OUT = REVIEW / "detail" / "front_sight"
MODULE = "front_sight"
MY_OBJS = ["cleaning_rod", "front_sight_block", "front_sight_post"]
MY_KEYS = MY_OBJS
TAG = "[FS]"


# ======================================================================================== Blender side
def _blender_build():
    import bpy
    from gunlib import bl
    from gunlib.parts import BuildCtx
    from rifle_common import SPEC
    import rifle_parts as RP
    import parts as PM
    from pipeline import lock as L
    L.assert_owner("AR01", "claude")
    for n in MY_OBJS:
        ob = bpy.data.objects.get(n)
        if ob is not None:
            bpy.data.objects.remove(ob, do_unlink=True)
    coll = bpy.data.collections.get("AR01_Parts") or bl.collection("AR01_Parts")
    ctx = BuildCtx(coll, GRIP, SPEC, MY_KEYS)
    built = PM.load(MODULE).build(SPEC, ctx)
    # round 2: the crops share the frame with the muzzle brake; rebuild it from its builder's current module
    # (read-only import, never edited here) so the blind pair is not judged on the baseline brake. On failure the
    # baseline brake stays and the report says so.
    import os
    mb_note = "baseline"
    if os.environ.get("FS_WITH_MB", "1") == "1":
        try:
            old = bpy.data.objects.get("muzzle_brake")
            keep = old.name if old else None
            if old is not None:
                old.name = "_mb_old"
            PM.load("muzzle_brake").build(SPEC, BuildCtx(coll, GRIP, SPEC, ["muzzle_brake"]))
            if bpy.data.objects.get("muzzle_brake") is not None and keep:
                bpy.data.objects.remove(bpy.data.objects["_mb_old"], do_unlink=True)
            mb_note = "muzzle_brake module (current)"
        except Exception as ex:                    # noqa: BLE001
            print(TAG, "muzzle_brake rebuild failed, baseline kept:", repr(ex)[:300])
            if bpy.data.objects.get("_mb_old") is not None:
                nb = bpy.data.objects.get("muzzle_brake")
                if nb is not None:
                    bpy.data.objects.remove(nb, do_unlink=True)
                bpy.data.objects["_mb_old"].name = "muzzle_brake"
    extra = {"rear_sight_leaf": ["rear_sight_slider"]}
    objs = []
    for k in RP.ORDER:
        for n in [k] + extra.get(k, []):
            ob = bpy.data.objects.get(n)
            if ob is not None and ob.type == "MESH":
                objs.append(ob)
    rep = {}
    for k, lst in built.items():
        for ob in lst:
            rep[ob.name] = bl.manifold_report(ob)
    bpy.ops.wm.save_as_mainfile(filepath=str(PRIV / "fs.blend"))
    bl.export_npz(objs, PRIV / "fs_tris.npz", GRIP, [o.name for o in objs])
    out = {"parts": rep, "part_triangles": sum(r["triangles"] for r in rep.values()), "muzzle_brake": mb_note,
           "rifle_triangles_npz": int(sum(bl.manifold_report(o)["triangles"] for o in objs))}
    (PRIV / "build_report.json").write_text(json.dumps(out, indent=1))
    print(TAG, "built", json.dumps(out))


def _blender_contacts():
    import bpy
    from gunlib import fit as F
    objs = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]
    G = F.geom(objs)
    pairs = F.pair_intersections(G)
    mine = [p for p in pairs if p["a"] in MY_OBJS or p["b"] in MY_OBJS]
    cp = [("barrel", "front_sight_block"), ("front_sight_block", "muzzle_brake"), ("cleaning_rod", "front_sight_block"),
          ("front_sight_block", "front_sight_post"), ("cleaning_rod", "gas_block"), ("cleaning_rod", "barrel"),
          ("front_sight_post", "barrel"), ("cleaning_rod", "handguard_front_band"), ("cleaning_rod", "lower_handguard")]
    cp = [tuple(sorted(p)) for p in cp if p[0] in G and p[1] in G]
    gaps = F.min_gaps(G, cp)
    where = {}
    import numpy as np
    for pr in mine:
        A, B = G[pr["a"]], G[pr["b"]]
        ov = F.tree(*A).overlap(F.tree(*B))
        cA = np.array([A[0][A[1][i]].mean(0) for i, _ in ov[:400]]) + np.asarray(GRIP)
        where[pr["a"] + "/" + pr["b"]] = {"min": cA.min(0).round(2).tolist(), "max": cA.max(0).round(2).tolist()}
    out = {"static_intersections_all": pairs, "static_intersections_mine": mine, "contact_gaps": gaps, "where": where}
    (PRIV / "contacts.json").write_text(json.dumps(out, indent=1, default=str))
    print(TAG, "contacts mine", json.dumps(mine), "where", json.dumps(where), "gaps", json.dumps(gaps, default=str))


def _blender_diag():
    """Print where this module's objects are not manifold (frame M, mm)."""
    import bpy
    import bmesh
    import numpy as np
    for n in MY_OBJS:
        ob = bpy.data.objects.get(n)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bad = []
        for e in bm.edges:
            k = len(e.link_faces)
            if k != 2:
                c = (np.array(e.verts[0].co) + np.array(e.verts[1].co)) / 2 * 1000.0 + np.asarray(GRIP)
                bad.append((k, [round(float(v), 2) for v in c]))
        bm.free()
        print(TAG, "diag", n, len(bad), bad[:40])


def _blender_edges():
    """Dump the edges the block's weighted passes would select (build with FS_RECIPE=none first)."""
    import bpy
    import bmesh
    import numpy as np
    import parts.front_sight as F
    ob = bpy.data.objects.get("front_sight_block")
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    out = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        a, b = np.array(e.verts[0].co) * 1000 + GRIP, np.array(e.verts[1].co) * 1000 + GRIP
        mid = (a + b) / 2
        d = b - a
        n1, n2 = np.array(e.link_faces[0].normal), np.array(e.link_faces[1].normal)
        dih = float(np.degrees(np.arccos(np.clip(n1 @ n2, -1, 1))))
        w1 = F.edge_weight(mid, d, n1, n2, dih)
        w2 = F.rim_weight(mid, d, n1, n2, dih)
        if w1 or w2:
            out.append([round(float(v), 2) for v in mid] + [round(float(np.linalg.norm(d)), 3), w1, w2])
    bm.free()
    (PRIV / "edges.json").write_text(json.dumps(out))
    print(TAG, "edges", len(out))


# ======================================================================================== plain Python side
def _run_blender(blend, mode):
    import gunlib
    log = PRIV / f"{mode}.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([gunlib.BLENDER, "-b", str(blend), "--factory-startup", "--python", str(Path(__file__).resolve()),
                        "--", mode], stdout=f, stderr=subprocess.STDOUT, check=False)
    txt = log.read_text(encoding="utf-8", errors="replace")
    if "Traceback" in txt or TAG not in txt:
        i = txt.find("Traceback")
        print(txt[i:i + 3000] if i >= 0 else txt[-3000:])
        raise SystemExit(f"blender {mode} failed, see {log}")
    for line in txt.splitlines():
        if line.startswith(TAG):
            print(line[:2500])


def kit():
    import gunlib
    from gunlib.detail import DetailKit
    import rifle_detail as RD
    cfg = {"sheet": str(SHEET), "panels": RD.PANELS, "parts": {MODULE: RD.parts_cfg()[MODULE]},
           "npz": str(PRIV / "fs_tris.npz"), "blend": str(PRIV / "fs.blend"), "offset_M": [float(v) for v in GRIP],
           "wood_slots": ["M_AR01_Furniture"], "review_dir": str(REVIEW / "detail"), "scratch_dir": str(PRIV),
           "blender": gunlib.BLENDER, "ss": 3, "samples": 96, "env": 0.55, "light": 1.35}
    return DetailKit(cfg)


def window_fixed():
    """The crop windows of the setup (round 0 framing), so every round compares the same reference crop."""
    d = json.loads((OUT / "before_crops.json").read_text())
    return {k: tuple(v["window_px"]) for k, v in d.items()}


def crop(tag):
    K = kit()
    fixed = window_fixed()
    K.window = lambda part, key: fixed[key]          # same framing every round
    res = K.render_part_crop([MODULE], tag)[MODULE]
    out = {"tag": tag, "crops": res}
    out.update(part_iou(K, tag))
    (OUT / f"{tag}_metrics.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: (v["silhouette_iou_window"], v["edges"]["f"]) for k, v in res.items()}),
          json.dumps(out.get("part_iou")))
    return out


def part_iou(K, tag):
    """Outline IoU in the part's own frame: the reference mask vs our projected silhouette restricted to the part's
    zone (our sight block + post projected and dilated, minus pixels only other parts cover), plus the zone above
    the barrel (the ears: only the sight forms the outline there) and the whole-window number."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage as ndi
    from gunlib import closeup as CU, compare as C
    out = {}
    V, T, lab, names = K.geometry()
    ids = [i for i, n in enumerate(names) if n in ("front_sight_block", "front_sight_post")]
    for key in K.cfg["parts"][MODULE]["panels"]:
        cam = K.part_camera(MODULE, key)
        P = K.panel(key)
        H, W = P.shape[:2]
        x0, y0, x1, y1 = K.window(MODULE, key)
        ref = K.mask(key)
        Tv = CU.visible_tris(cam, V, T)
        allc = C.raster_tris(cam.project(V), Tv, (H, W), ss=2) > 0.5
        sel = np.isin(lab, ids)
        mine = C.raster_tris(cam.project(V), CU.visible_tris(cam, V, T[sel]), (H, W), ss=2) > 0.5
        others = C.raster_tris(cam.project(V), CU.visible_tris(cam, V, T[~sel]), (H, W), ss=2) > 0.5
        zone = ndi.binary_dilation(mine, iterations=6) & ~(others & ~mine)
        roi = np.zeros((H, W), bool)
        roi[y0:y1, x0:x1] = True
        z = zone & roi
        # ears zone: rows above the highest pixel of any other part inside the sight's columns
        cols = np.nonzero(mine.any(0))[0]
        oth_rows = np.nonzero(others[:, cols.min():cols.max() + 1].any(1))[0]
        top_other = int(oth_rows.min()) if len(oth_rows) else H
        ez = z.copy()
        ez[top_other - 2:, :] = False
        fit = fit_iou(allc, ref, z)
        out[key] = {"iou_part_zone": round(C.iou(allc, ref, z), 4), "zone_px": int(z.sum()),
                    "iou_part_zone_fit": fit["iou"], "fit_similarity": fit["sim"], "iou_part_zone_fit_aniso": fit["iou_aniso"],
                    "fit_aniso": fit["aniso"],
                    "iou_ears_zone": round(C.iou(allc, ref, ez), 4), "ears_zone_px": int(ez.sum()),
                    "iou_ears_zone_fit_r1style": ears_fit_r1(allc, ref, ez),
                    "iou_window_proj": round(C.iou(allc, ref, roi), 4)}
        rgb = P[y0:y1, x0:x1].copy().astype(float)
        a, r, zz = allc[y0:y1, x0:x1], ref[y0:y1, x0:x1], z[y0:y1, x0:x1]
        img = rgb * 0.6
        img[a & ~r & zz] = [255, 80, 0]
        img[r & ~a & zz] = [0, 120, 255]
        img[~zz] *= 0.5
        k = max(2, int(round(480 / (y1 - y0))))
        Image.fromarray(img.clip(0, 255).astype(np.uint8)).resize(((x1 - x0) * k, (y1 - y0) * k), Image.NEAREST).save(
            OUT / f"{tag}_partzone_{key}.png")
    return {"part_iou": out}


def fit_iou(ours, ref, zone):
    """Outline IoU in the part's own frame: our projected mask moved by a 2D similarity (shift +-16 px, scale
    0.88-1.12 about the zone centroid) to best match the close-up trace inside the zone, so the camera solve's
    residual (landmark RMS ~17 px on c3) is not scored as shape error. Also an anisotropic fit (sx, sy) for info."""
    import numpy as np
    from scipy import ndimage as ndi
    ys, xs = np.nonzero(zone)
    cy, cx = ys.mean(), xs.mean()
    o = ours.astype(np.float32)
    r = ref & zone

    def score(sx, sy, dx, dy):
        M = np.array([[1.0 / sy, 0.0], [0.0, 1.0 / sx]])
        off = np.array([cy - (cy + dy) / sy, cx - (cx + dx) / sx])
        w = ndi.affine_transform(o, M, offset=off, order=1) > 0.5
        w &= zone
        u = (w | r).sum()
        return (w & r).sum() / u if u else 0.0

    best = (0.0, 1.0, 1.0, 0, 0)
    for s in np.linspace(0.88, 1.12, 7):
        for dx in range(-16, 17, 4):
            for dy in range(-16, 17, 4):
                v = score(s, s, dx, dy)
                if v > best[0]:
                    best = (v, s, s, dx, dy)
    v, s, _, dx0, dy0 = best
    for s2 in np.linspace(s - 0.03, s + 0.03, 5):
        for dx in range(dx0 - 3, dx0 + 4):
            for dy in range(dy0 - 3, dy0 + 4):
                q = score(s2, s2, dx, dy)
                if q > best[0]:
                    best = (q, s2, s2, dx, dy)
    sim = best
    ab = sim
    for sx in np.linspace(sim[1] - 0.12, sim[1] + 0.12, 7):
        for sy in np.linspace(sim[2] - 0.12, sim[2] + 0.12, 7):
            for dx in range(sim[3] - 4, sim[3] + 5, 2):
                for dy in range(sim[4] - 4, sim[4] + 5, 2):
                    q = score(sx, sy, dx, dy)
                    if q > ab[0]:
                        ab = (q, sx, sy, dx, dy)
    return {"iou": round(float(sim[0]), 4), "sim": [round(float(sim[1]), 3), int(sim[3]), int(sim[4])],
            "iou_aniso": round(float(ab[0]), 4), "aniso": [round(float(ab[1]), 3), round(float(ab[2]), 3), int(ab[3]), int(ab[4])]}


def ears_fit_r1(ours, ref, zone):
    """Round-1's own-frame number for comparison: ears zone, own-scale fit sx 0.80-1.16, sy 0.90-1.16, shift +-12 px
    about the zone centroid (grid 0.04 / 3 px, then refined)."""
    import numpy as np
    from scipy import ndimage as ndi
    ys, xs = np.nonzero(zone)
    cy, cx = ys.mean(), xs.mean()
    o = ours.astype(np.float32)
    r = ref & zone

    def score(sx, sy, dx, dy):
        M = np.array([[1.0 / sy, 0.0], [0.0, 1.0 / sx]])
        off = np.array([cy - (cy + dy) / sy, cx - (cx + dx) / sx])
        w = (ndi.affine_transform(o, M, offset=off, order=1) > 0.5) & zone
        u = (w | r).sum()
        return (w & r).sum() / u if u else 0.0
    best = (0.0, 1, 1, 0, 0)
    for a in np.arange(0.80, 1.161, 0.04):
        for b in np.arange(0.90, 1.161, 0.04):
            for dx in range(-12, 13, 3):
                for dy in range(-12, 13, 3):
                    v = score(a, b, dx, dy)
                    if v > best[0]:
                        best = (v, a, b, dx, dy)
    v, a0, b0, dx0, dy0 = best
    for a in np.clip(np.arange(a0 - 0.02, a0 + 0.021, 0.01), 0.80, 1.16):
        for b in np.clip(np.arange(b0 - 0.02, b0 + 0.021, 0.01), 0.90, 1.16):
            for dx in range(dx0 - 2, dx0 + 3):
                for dy in range(dy0 - 2, dy0 + 3):
                    q = score(a, b, dx, dy)
                    if q > best[0]:
                        best = (q, a, b, dx, dy)
    return [round(float(best[0]), 4), round(float(best[1]), 2), round(float(best[2]), 2), int(best[3]), int(best[4])]


def l2(tag):
    import rifle_silhouette as RS
    res = RS.run(str(PRIV / "fs_tris.npz"), "detail/front_sight/l2", tag)
    side = res["views"]["side"]
    out = {"front_sight_block": side["parts"].get("front_sight_block"), "cleaning_rod": side["parts"].get("cleaning_rod"),
           "muzzle_brake": side["parts"].get("muzzle_brake"), "barrel": side["parts"].get("barrel"),
           "side_iou_fit": side["iou_fit"], "side_contour": side["contour_px"],
           "top_iou_fit_valid": res["views"]["top"]["iou_fit_valid"], "triangles_total": res["triangles"],
           "all_parts_pass": all(v["pass"] for v in side["parts"].values()),
           "failing": [k for k, v in side["parts"].items() if not v["pass"]]}
    (PRIV / f"l2{('_' + tag) if tag else ''}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out))
    return out


def main():
    a = sys.argv[1:]
    if IN_BLENDER:
        mode = (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["build"])[0]
        {"build": _blender_build, "contacts": _blender_contacts, "diag": _blender_diag, "edges": _blender_edges}[mode]()
        return
    cmd = a[0] if a else "build"
    tag = a[a.index("--tag") + 1] if "--tag" in a else "cur"
    if cmd == "build":
        _run_blender(PRIV / "base.blend", "build")
    elif cmd == "crop":
        crop(tag)
    elif cmd == "l2":
        l2(tag)
    elif cmd in ("contacts", "diag", "edges"):
        _run_blender(PRIV / "fs.blend", cmd)


if __name__ == "__main__":
    main()
