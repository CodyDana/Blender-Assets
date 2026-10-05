"""Selector detail loop (review only; plain Python, renders through headless Blender):

    py -3 -B Scripts/guns/rifle/parts/selector_dev.py overlay            trace overlay on 8x c1 zoom
    py -3 -B Scripts/guns/rifle/parts/selector_dev.py fit                c1 trace -> side view similarity fit
    py -3 -B Scripts/guns/rifle/parts/selector_dev.py build  [--tag r1]  my selector into a private copy of the form
                                                                         blend (+ the c1-posed copy), npz, B3 sweep
    py -3 -B Scripts/guns/rifle/parts/selector_dev.py render [--tag r1]  ROUGH LOOK crops at the selector's c1 / q34
                                                                         cameras + gates (IoU vs trace, tris, sweep)
    py -3 -B Scripts/guns/rifle/parts/selector_dev.py blind  --tag r1    blind pair (ours = A) + key

Works on a PRIVATE copy (scratch/detail/selector/): the shared Assets/Guns/AR01.blend is only read, the selector
object in it is replaced by the one parts/selector.py builds now, so parallel part builders never collide.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent              # Scripts/guns/rifle/parts
RIFLE = HERE.parent
sys.path.insert(0, str(RIFLE))
sys.path.insert(0, str(HERE))
from rifle_common import SHEET, SCRATCH, REVIEW, BLEND, GRIP, SPEC, ROOT  # noqa: E402

import gunlib  # noqa: E402
from gunlib import closeup as CU  # noqa: E402
from gunlib import compare as C  # noqa: E402
import selector_trace as ST  # noqa: E402

PIVOT = (282.8, -7.8)
WS = SCRATCH / "detail" / "selector"            # private scratch
RV = REVIEW / "detail" / "selector"
CAMS = SCRATCH / "detail" / "cameras"
WS.mkdir(parents=True, exist_ok=True)
RV.mkdir(parents=True, exist_ok=True)
FIT_JSON = WS / "fit.json"


def c1_panel():
    from PIL import Image
    im = Image.open(SHEET).convert("RGB")
    return im.crop((9, 629, 298, 991))


def cam_json(key):
    return json.loads((CAMS / f"selector__{key}.json").read_text())["camera"]


# ------------------------------------------------------------------------------------------ overlay
def cmd_overlay(a):
    from PIL import ImageDraw
    P = c1_panel()
    x0, y0, x1, y1 = 62, 86, 242, 136
    s = 8
    im = P.crop((x0, y0, x1, y1)).resize(((x1 - x0) * s, (y1 - y0) * s), 3)
    d = ImageDraw.Draw(im)

    def T(p):
        return ((p[0] - x0 + 0.5) * s, (p[1] - y0 + 0.5) * s)

    O = ST.c1_outline_px()
    d.line([T(p) for p in np.vstack([O, O[:1]])], fill=(255, 120, 0), width=2)
    cx, cy = ST.C1_PIVOT_PX
    for r, col in ((ST.C1_RING_R_PX, (0, 255, 255)), (ST.C1_DOME_R_PX, (255, 0, 255))):
        d.ellipse([T((cx - r, cy - r)), T((cx + r, cy + r))], outline=col, width=2)
    d.line([T(p) for p in ST.C1_CREASE_PX], fill=(0, 255, 0), width=2)
    bx, by = ST.C1_NOSE_BOSS_PX
    r = ST.C1_NOSE_BOSS_R_PX
    d.ellipse([T((bx - r, by - r)), T((bx + r, by + r))], outline=(0, 255, 255), width=2)
    d.line([T(p) for p in ST.C1_BEND_PX], fill=(255, 255, 0), width=1)
    out = WS / "trace_overlay.png"
    im.save(out)
    print(out)


# ------------------------------------------------------------------------------------------ fit
def side_outline():
    return np.array(SPEC.feature("selector", "face_outline_M")["XZ"], float)


def c1_rel(plane_y=-24.5):
    return ST.to_lever_xz(cam_json("c1"), ST.c1_outline_px(), plane_y, PIVOT)


def cmd_fit(a):
    rel = c1_rel()
    deg, k, iou = ST.fit_to_side(rel, side_outline(), PIVOT)
    L = float(np.linalg.norm(rel, axis=1).max())
    out = {"deg_c1_to_rest": deg, "scale_c1_to_side": k, "iou_vs_side_outline": round(iou, 4),
           "c1_len_from_pivot_mm_at_cam_scale": round(L, 2), "len_after_mm": round(L * k, 2),
           "note": "c1 lever outline (unprojected with the selector c1 camera, anchored on the pivot) rotated by deg "
                   "(front up) and scaled by k about the pivot to best match the side view's lever outline"}
    FIT_JSON.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


# ------------------------------------------------------------------------------------------ build (Blender)
BUILD_PY = r'''
import sys, json, math
from pathlib import Path
sys.path.insert(0, r"{rifle}")
import bpy
import numpy as np
from rifle_common import GRIP, SPEC
from gunlib import bl, fit as F
from gunlib.parts import BuildCtx
import parts.selector as SEL
old = bpy.data.objects.get("selector")
coll = old.users_collection[0] if old else bl.collection("AR01_Parts")
if old:
    bpy.data.objects.remove(old, do_unlink=True)
ctx = BuildCtx(coll, GRIP, SPEC, ["selector"])
objs = SEL.build(SPEC, ctx)["selector"]
ob = objs[0]
rep = bl.manifold_report(ob)
print("[SEL] report", json.dumps(rep))
bpy.ops.wm.save_as_mainfile(filepath=r"{out_rest}")
meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]
bl.export_npz(meshes, Path(r"{npz}"), GRIP, [o.name for o in meshes])
# B3 selector sweep (same rule as rifle_b3.py) + static gaps
G = F.geom(meshes)
piv = np.asarray([282.8, 0, -7.8], float) - GRIP
mov = {{"selector": G["selector"]}}
fixed = {{n: v for n, v in G.items() if n != "selector"}}
lo, hi = 0.10, 0.30
V = G["selector"][0]
rmax = float(np.linalg.norm(V - piv, axis=1).max())
step = min(1.0, math.degrees(lo / rmax))
vals = np.arange(0.0, 32.0 + 1e-9, step) if {sweep} else np.array([0.0, 16.0, 32.0])
if vals[-1] < 32.0 - 1e-9:
    vals = np.r_[vals, 32.0]
recs, summ = F.sweep(mov, fixed, lambda v: F.rot_matrix(piv, [0, 1, 0], v), vals, clearance_every=1)
summ["row_mm"] = [lo, hi]
summ["r_max_mm"] = round(rmax, 2)
summ["pass"] = summ["intersecting_steps"] == 0 and summ["min_clearance_mm"] >= lo - 1e-4 and summ["min_clearance_mm"] <= hi + 1e-4
pairs = [p for p in F.pair_intersections(G) if "selector" in json.dumps(p)]
gaps = F.min_gaps(G, [("receiver", "selector"), ("rivets", "selector")])
worst = sorted([r for r in recs if r["intersections"]], key=lambda r: -r["intersections"])[:8]
Path(r"{b3}").write_text(json.dumps({{"summary": summ, "static_pairs_with_selector": pairs, "gaps": gaps,
                                      "worst_steps": worst, "manifold": rep}}, indent=1, default=str))
print("[SEL] sweep", json.dumps(summ))
# posed copy for the c1 render: front end down by the c1 pose angle
pose = float({pose})
import mathutils
M = mathutils.Matrix.Translation(mathutils.Vector(piv / 1000.0)) @ mathutils.Matrix.Rotation(math.radians(pose), 4, "Y") @ mathutils.Matrix.Translation(mathutils.Vector(-piv / 1000.0))
ob.data.transform(M)
ob.data.update()
bpy.ops.wm.save_as_mainfile(filepath=r"{out_posed}")
print("[SEL] BUILD_DONE")
'''


def blend_paths(tag):
    t = tag or "cur"
    return WS / f"AR01_sel_{t}.blend", WS / f"AR01_sel_{t}_c1pose.blend", WS / f"form_tris_{t}.npz", WS / f"b3_{t}.json"


def c1_pose_deg():
    """Rotation about +Y (Blender / frame M) that swings the lever's front end DOWN by the c1 pose angle."""
    f = json.loads(FIT_JSON.read_text())
    return float(f["deg_c1_to_rest"])           # rotation about +Y by +deg moves +X points toward -Z


def cmd_build(a):
    out_rest, out_posed, npz, b3 = blend_paths(a.tag)
    code = BUILD_PY.format(rifle=str(RIFLE), out_rest=str(out_rest), out_posed=str(out_posed), npz=str(npz),
                           b3=str(b3), pose=c1_pose_deg(), sweep=not a.no_sweep)
    sp = WS / f"build_job_{a.tag or 'cur'}.py"
    sp.write_text(code)
    log = WS / f"build_{a.tag or 'cur'}.log"
    t0 = time.time()
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([gunlib.BLENDER, "-b", str(BLEND), "--factory-startup", "--python", str(sp)],
                       stdout=f, stderr=subprocess.STDOUT, check=False, cwd=str(ROOT))
    txt = log.read_text(encoding="utf-8", errors="replace")
    for ln in txt.splitlines():
        if ln.startswith("[SEL]") or "Error" in ln:
            print(ln[:400])
    if "BUILD_DONE" not in txt:
        print("BUILD FAILED, see", log)
        i = txt.find("Traceback")
        print(txt[i:i + 3000])
        sys.exit(1)
    print("build %.1fs" % (time.time() - t0))


# ------------------------------------------------------------------------------------------ render + gates
def my_camera(key):
    """The selector's camera for this panel. q34: the fixed 3/4 camera. c1: the panel's rotation, with scale and
    offset solved on the selector itself (pivot centre + the lever's length in c1), since c1 is not to scale and
    draws the selector ~12 px further back on the receiver than the receiver-solved camera puts it."""
    d = dict(cam_json(key))
    if key != "c1":
        return d
    f = json.loads(FIT_JSON.read_text())
    k = float(f["scale_c1_to_side"])
    cam = CU.cam_from_json(d)
    s_new = cam.s / k                       # our (side-scaled) lever spans the c1 lever's px length
    piv3 = np.array([PIVOT[0], -24.5, PIVOT[1]])
    pu = cam.project(piv3[None])[0]
    tu, tv = ST.C1_PIVOT_PX
    # keep R; new c0 = pivot point, new c0_px = traced pivot
    d["px_per_mm"] = s_new
    d["c0_M"] = piv3.tolist()
    d["c0_px"] = [tu, tv]
    cam2 = CU.OrthoCam(cam.R, piv3, s_new, tu, tv, cam.W, cam.H)
    out = cam2.to_json()
    out.update({"c0_M": piv3.tolist(), "c0_px": [tu, tv]})
    out["note"] = f"selector c1 camera: scale {cam.s:.4f} -> {s_new:.4f} px/mm, pivot {pu.round(1).tolist()} -> {[tu, tv]}"
    return out


def kit_for(tag, blend):
    import rifle_detail as RD
    from gunlib.detail import DetailKit
    cfg = dict(RD.kit().cfg)
    _, _, npz, _ = blend_paths(tag)
    cfg.update({"npz": str(npz), "blend": str(blend), "scratch_dir": str(WS / "kit"), "review_dir": str(REVIEW / "detail")})
    cfg["parts"] = {"selector": dict(cfg["parts"]["selector"])}
    K = DetailKit(cfg)
    (WS / "kit" / "cameras").mkdir(parents=True, exist_ok=True)
    for key in ("c1", "q34"):
        cj = my_camera(key)
        (WS / "kit" / "cameras" / f"selector__{key}.json").write_text(json.dumps({"panel": key, "part": "selector",
                                                                                 "camera": cj}, indent=1))
    return K


def trace_mask_px(cam_d, ss=4):
    """c1 trace polygon mask at panel px x ss (pixel-centre coords, same convention as compare.raster_tris)."""
    from PIL import Image, ImageDraw
    W, H = cam_d["panel_px"]
    O = (ST.c1_outline_px() + 0.5) * ss
    im = Image.new("L", (W * ss, H * ss), 0)
    ImageDraw.Draw(im).polygon([tuple(p) for p in O], fill=255)
    return np.asarray(im) > 127


def our_mask_px(cam_d, npz, pose_deg, ss=4):
    D = np.load(npz)
    names = [str(n) for n in D["names"]]
    i = names.index("selector")
    V, T, lab = D["V"], D["T"], D["lab"]
    T = T[lab == i]
    # rotate the rest-pose lever to the c1 pose (front down) about the pivot (frame M)
    P = V.copy()
    t = math.radians(pose_deg)
    dx, dz = P[:, 0] - PIVOT[0], P[:, 2] - PIVOT[1]
    P[:, 0] = PIVOT[0] + dx * math.cos(t) + dz * math.sin(t)
    P[:, 2] = PIVOT[1] - dx * math.sin(t) + dz * math.cos(t)
    cam = CU.cam_from_json(cam_d)
    W, H = cam_d["panel_px"]
    m = C.raster_tris(cam.project(P), T, (H, W), ss=ss, coverage=False)
    return m, P, T, cam


def lever_frame_iou(npz):
    """Part-frame IoU: our lever's XZ silhouette at rest vs the c1 trace mapped into the lever frame by the fitted
    similarity (pose + scale) - i.e. shape agreement independent of the close-up's pose and scale."""
    f = json.loads(FIT_JSON.read_text())
    tr = ST.similarity(c1_rel(), f["deg_c1_to_rest"], f["scale_c1_to_side"], PIVOT)
    D = np.load(npz)
    names = [str(n) for n in D["names"]]
    i = names.index("selector")
    V, T = D["V"], D["T"][D["lab"] == i]
    res = 0.1
    lo = np.minimum(V[np.unique(T)][:, [0, 2]].min(0), tr.min(0)) - 1
    hi = np.maximum(V[np.unique(T)][:, [0, 2]].max(0), tr.max(0)) + 1
    Wd, Hd = int((hi[0] - lo[0]) / res) + 1, int((hi[1] - lo[1]) / res) + 1
    # rasterise our triangles in XZ
    uv = np.c_[(V[:, 0] - lo[0]) / res - 0.5, (V[:, 2] - lo[1]) / res - 0.5]
    ours = C.raster_tris(uv, T, (Hd, Wd), ss=1) > 0.5
    ref = ST.poly_mask(tr, lo[0], lo[1], res, Wd, Hd)
    # the trace is the plate outline (no bent-out tab foreshortening, no head): compare outlines only
    side = ST.poly_mask(side_outline(), lo[0], lo[1], res, Wd, Hd)
    return {"iou_vs_c1_trace_lever_frame": round(float((ours & ref).sum() / max(1, (ours | ref).sum())), 4),
            "iou_vs_side_trace": round(float((ours & side).sum() / max(1, (ours | side).sum())), 4),
            "iou_c1_trace_vs_side_trace": round(float((ref & side).sum() / max(1, (ref | side).sum())), 4)}


def cmd_render(a):
    tag = a.tag or "cur"
    out_rest, out_posed, npz, b3 = blend_paths(a.tag)
    K = kit_for(a.tag, out_rest)
    shots_c1 = [K._shot("selector", "c1", tag)]
    shots_q = [K._shot("selector", "q34", tag)]
    # the rest blend for both shots: since the integration round the kit's c1 shot carries the c1 pose itself
    # (rifle_detail.SEL_C1_POSE); the c1-posed blend would pose it twice
    if not shots_c1[0].get("poses"):
        K.cfg["blend"] = str(out_posed)
    else:
        K.cfg["blend"] = str(out_rest)
    K.run_blender(shots_c1, f"render_c1_{tag}")
    K.cfg["blend"] = str(out_rest)
    K.run_blender(shots_q, f"render_q34_{tag}")
    res = K.render_part_crop(["selector"], tag, render=False)["selector"]
    # IoU vs the c1 trace in panel px (our posed silhouette at the selector camera)
    cam_d = my_camera("c1")
    ss = 4
    ref = trace_mask_px(cam_d, ss)
    ours, _, _, _ = our_mask_px(cam_d, npz, c1_pose_deg(), ss)
    x0, y0, x1, y1 = res["c1"]["window_px"]
    roi = np.zeros_like(ref)
    roi[y0 * ss:y1 * ss, x0 * ss:x1 * ss] = True
    iou_c1 = float(((ref & ours) & roi).sum() / max(1, ((ref | ours) & roi).sum()))
    # silhouette overlay at the crop
    from PIL import Image
    ov = np.zeros((ref.shape[0], ref.shape[1], 3), np.uint8)
    ov[ref & ~ours] = (60, 120, 255)
    ov[ours & ~ref] = (255, 120, 0)
    ov[ours & ref] = (200, 200, 200)
    Image.fromarray(ov[y0 * ss:y1 * ss, x0 * ss:x1 * ss]).save(RV / f"{tag}_iou_c1.png")
    fr = lever_frame_iou(npz)
    b3d = json.loads(b3.read_text())
    tris = int(np.isin(np.load(npz)["lab"], [[str(n) for n in np.load(npz)["names"]].index("selector")]).sum())
    out = {"tag": tag, "iou_vs_c1_trace_panel_px": round(iou_c1, 4), **fr, "triangles": tris,
           "manifold": b3d["manifold"], "sweep": b3d["summary"], "static_pairs_with_selector": b3d["static_pairs_with_selector"],
           "gaps": b3d["gaps"], "crops": res, "fit": json.loads(FIT_JSON.read_text()),
           "camera_c1": cam_d.get("note")}
    (RV / f"{tag}_result.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k not in ("crops",)}, indent=1, default=str)[:3000])
    for k, v in res.items():
        print(k, v["silhouette_iou_window"], v["edges"])


def cmd_blind(a):
    """Blind pair: ours goes in the slot --ours (A or B), the c1 reference crop in the other; key outside the folder."""
    tag = a.tag
    bd = REVIEW / "detail_blind" / f"selector_{tag}"
    bd.mkdir(parents=True, exist_ok=True)
    src = a.src or tag                              # which render tag goes in (e.g. --tag r1 --src final)
    ours_slot = a.ours.upper()
    ref_slot = "A" if ours_slot == "B" else "B"
    shutil.copyfile(RV / f"{src}_ours_c1.png", bd / f"{ours_slot}.png")
    shutil.copyfile(RV / "ref_c1.png", bd / f"{ref_slot}.png")
    from PIL import Image
    sa, sb = Image.open(bd / "A.png").size, Image.open(bd / "B.png").size
    assert sa == sb, (sa, sb)
    key = {"part": "selector", "round": tag, "panel": "c1",
           ours_slot: "ours (ROUGH LOOK render, c1-solved selector camera, lever posed at the c1 angle)",
           ref_slot: "reference (sheet c1 crop)", "ours_is": ours_slot, "size_px": list(sa),
           "files": {"A": str((bd / "A.png").relative_to(ROOT)), "B": str((bd / "B.png").relative_to(ROOT))},
           "source_render": f"review/detail/selector/{src}_ours_c1.png",
           "date": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (RV / f"key_{tag}.json").write_text(json.dumps(key, indent=1))
    print(json.dumps(key, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["overlay", "fit", "build", "render", "blind"])
    ap.add_argument("--tag", default="")
    ap.add_argument("--no-sweep", action="store_true", help="build: 3 sweep samples only (fast look loop)")
    ap.add_argument("--ours", default="A", choices=["A", "B", "a", "b"], help="blind: slot for our render")
    ap.add_argument("--src", default="", help="blind: render tag to copy as A (default: --tag)")
    a = ap.parse_args()
    {"overlay": cmd_overlay, "fit": cmd_fit, "build": cmd_build, "render": cmd_render, "blind": cmd_blind}[a.cmd](a)


if __name__ == "__main__":
    main()
