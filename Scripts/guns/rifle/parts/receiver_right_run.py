"""Private detail loop for the part receiver_right (detail pass round 1): rebuild ONLY this module's objects into a
snapshot of the form build, render its close-up crops in the ROUGH LOOK and measure them, without touching the
shared Assets/Guns/AR01.blend, scratch/form_tris.npz or the shared detail scratch (other part builders run in
parallel on the same files).

    py -3 -B Scripts/guns/rifle/parts/receiver_right_run.py iter --tag r1i1 [--no-build] [--no-render]
    py -3 -B Scripts/guns/rifle/parts/receiver_right_run.py b3            (B3 bolt / selector / catch sweeps)
    py -3 -B Scripts/guns/rifle/parts/receiver_right_run.py sil           (side L2 per-part silhouettes)

Inputs : WorkFiles/guns/rifle/scratch/detail/receiver_right/base.blend (+ base_tris.npz): snapshot of the form build
         cameras/receiver_right__<panel>.json (the solved part cameras of the detail setup)
Outputs: scratch/detail/receiver_right/rr.blend + rr_tris.npz + build_report.json (+ renders, job logs)
         review/detail/receiver_right/<tag>_{ours,pair,edges}_<panel>.png, <tag>_crops.json, <tag>_metrics.json
Inside Blender (called by the driver): blender -b base.blend --factory-startup --python <this> -- --blender-build
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent             # Scripts/guns/rifle/parts
RIFLE = HERE.parent
sys.path.insert(0, str(RIFLE))
from rifle_common import ROOT, SPEC, GRIP, SCRATCH, REVIEW, SHEET  # noqa: E402

PART = "receiver_right"
WORK = SCRATCH / "detail" / PART
BASE_BLEND = WORK / "base.blend"
BASE_NPZ = WORK / "base_tris.npz"
RR_BLEND = WORK / "rr.blend"
RR_NPZ = WORK / "rr_tris.npz"
OUT = REVIEW / "detail" / PART
# crop windows of the detail setup (before_crops.json), fixed so every iteration has identical framing
WINDOWS = {"c1": (0, 0, 290, 301), "c2": (0, 17, 277, 363), "q34": (124, 0, 382, 166)}


# ============================================================================================ Blender side
def blender_build():
    import bpy
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock as L
    L.assert_owner("AR01", "claude")
    import numpy as np
    from gunlib import bl
    from gunlib.parts import BuildCtx
    import parts as PM
    mod = PM.load(PART)
    names = PM.objects_of(PART)
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    coll = bpy.data.collections.get("AR01_Parts") or bl.collection("AR01_Parts")
    ctx = BuildCtx(coll, GRIP, SPEC)
    t0 = time.time()
    mod.build(SPEC, ctx)
    D = np.load(BASE_NPZ)
    order = [str(n) for n in D["names"]]
    objs = [bpy.data.objects[n] for n in order if n in bpy.data.objects]
    extra = [o for o in coll.objects if o.type == "MESH" and o.name not in order and not o.name.startswith("_")]
    objs += extra
    rep = {}
    for ob in objs:
        if ob.name in names or ob in extra:
            r = bl.manifold_report(ob)
            rep[ob.name] = r
            print("[rr] part %-22s tris %6d  boundary %d  multi %d  shells %d" % (
                ob.name, r["triangles"], r["boundary_edges"], r["multi_face_edges"], r["shells"]))
    total = sum(len(o.data.loop_triangles) if o.data.loop_triangles else 0 for o in objs)
    bl.export_npz(objs, RR_NPZ, GRIP, [o.name for o in objs])
    D2 = np.load(RR_NPZ)
    rep["_total_tris"] = int(len(D2["T"]))
    rep["_part_tris"] = int(sum(v["triangles"] for k, v in rep.items() if not k.startswith("_")))
    rep["_seconds"] = round(time.time() - t0, 1)
    (WORK / "build_report.json").write_text(json.dumps(rep, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(RR_BLEND))
    print("[rr] total tris", rep["_total_tris"], "part tris", rep["_part_tris"], "(%d)" % total)
    print("[rr] BUILD_DONE")


# ============================================================================================ driver side
def run_blender(args, log):
    import gunlib
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([gunlib.BLENDER, "-b", *args], stdout=f, stderr=subprocess.STDOUT, check=False)
    txt = Path(log).read_text(encoding="utf-8", errors="replace")
    if "Traceback" in txt:
        i = txt.index("Traceback")
        raise RuntimeError(f"blender failed ({log}):\n" + txt[i:i + 3000])
    return txt


def build():
    txt = run_blender([str(BASE_BLEND), "--factory-startup", "--python", str(Path(__file__).resolve()), "--",
                       "--blender-build"], WORK / "build.log")
    if "BUILD_DONE" not in txt:
        raise RuntimeError("build did not finish, see " + str(WORK / "build.log"))
    return json.loads((WORK / "build_report.json").read_text())


def kit():
    import rifle_detail as RD
    K = RD.kit()
    K.cfg["npz"] = str(RR_NPZ)
    K.cfg["blend"] = str(RR_BLEND)
    K.scratch = WORK
    (WORK / "renders").mkdir(parents=True, exist_ok=True)
    K.window = lambda part, key: WINDOWS[key]           # identical framing every iteration
    return K


def roi_for(K, key, names):
    """The receiver group's own window: the projected box of the named objects inside the crop window, for c1 cut at
    the receiver bottom (below it the grip, guard and magazine own the pixels)."""
    import numpy as np
    from gunlib import closeup as CU
    cam = K.part_camera(PART, key)
    V, T = K.subset(names)
    uv = cam.project(V[np.unique(T)])
    x0, y0, x1, y1 = WINDOWS[key]
    u0, v0 = max(x0, int(np.floor(uv[:, 0].min()))), max(y0, int(np.floor(uv[:, 1].min())))
    u1, v1 = min(x1, int(np.ceil(uv[:, 0].max())) + 1), min(y1, int(np.ceil(uv[:, 1].max())) + 1)
    if key == "c1":                                    # receiver bottom at the grip / guard
        vb = cam.project(np.array([[300.0, -20.75, -31.5], [360.0, -20.75, -29.5]]))[:, 1].max()
        v1 = min(v1, int(np.ceil(vb)))
    return u0, v0, u1, v1


def metrics(K, tag):
    import numpy as np
    from PIL import Image
    from scipy import ndimage as ndi
    from gunlib import closeup as CU
    from gunlib import compare as C
    res = {}
    for key in WINDOWS:
        P = K.panel(key)
        H, W = P.shape[:2]
        rgba = np.asarray(Image.open(WORK / "renders" / f"{PART}__{key}_{tag}.png").convert("RGBA"))
        _, _, _, bg = CU.fit_background(P)
        ours = CU.composite_on(bg, rgba, K.ss)
        our_small = CU.downscale(ours, K.ss)
        alpha = CU.downscale(np.repeat(rgba[:, :, 3:4], 3, 2).astype(np.uint8), K.ss)[:, :, 0] / 255.0
        sil_o = alpha > 0.5
        ref_m = K.mask(key)
        u0, v0, u1, v1 = roi_for(K, key, ["receiver", "dust_cover", "bolt_carrier"])
        roi = np.zeros((H, W), bool)
        roi[v0:v1, u0:u1] = True
        er, _ = CU.canny(P.mean(2), 1.4, 88.0, mask=ndi.binary_erosion(ref_m, iterations=2))
        eo, _ = CU.canny(our_small.mean(2), 1.4, 88.0, mask=ndi.binary_erosion(sil_o, iterations=2))
        em = CU.edge_metrics(er, eo, roi, 2.0)
        res[key] = {"roi_px": [u0, v0, u1, v1], "part_silhouette_iou": round(C.iou(sil_o, ref_m, roi), 4),
                    "part_edges": em}
    return res


def iterate(tag, do_build=True, do_render=True):
    out = {"tag": tag, "date": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if do_build:
        out["build"] = build()
    else:
        out["build"] = json.loads((WORK / "build_report.json").read_text())
    K = kit()
    crops = K.render_part_crop(PART, tag, render=do_render)[PART]
    out["crops"] = crops
    out["metrics"] = metrics(K, tag)
    (OUT / f"{tag}_metrics.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"tris": out["build"].get("_part_tris"), "total": out["build"].get("_total_tris"),
                      "metrics": out["metrics"],
                      "window_iou": {k: v["silhouette_iou_window"] for k, v in crops.items()}}, indent=1))
    return out


def run_redirected(name):
    """Run a rifle gate script (rifle_<name>.py) on rr.blend with SCRATCH redirected to this part's folder."""
    script = WORK / f"_{name}_wrap.py"
    script.write_text(
        "import sys, runpy\n"
        f"sys.path.insert(0, r'{RIFLE}')\n"
        "import rifle_common\n"
        f"from pathlib import Path\nrifle_common.SCRATCH = Path(r'{WORK}')\n"
        f"runpy.run_path(r'{RIFLE / f'rifle_{name}.py'}', run_name='__main__')\n")
    return run_blender([str(RR_BLEND), "--factory-startup", "--python", str(script)], WORK / f"{name}.log")


def measure():
    """L3 features / L4 dimensions (rifle_measure.py) on rr.blend -> this part's measure_result.json."""
    run_redirected("measure")
    r = json.loads((WORK / "measure_result.json").read_text())
    for f in r["L3"]:
        print("[L3]", f["pass"], f["feature"], f["measured"], "err", f["error_mm"])
    bad = [f for f in r.get("L4", []) if not f.get("pass", True)]
    print("[L4] failures:", bad)
    return r


def b3():
    """B3 sweeps on rr.blend; rifle_b3.py runs with SCRATCH redirected to this part's folder."""
    run_redirected("b3")
    r = json.loads((WORK / "b3_result.json").read_text())
    for g, d in r["groups"].items():
        s = d["summary"]
        print(g, {k: s[k] for k in ("intersecting_steps", "min_clearance_mm", "min_with", "pass")})
    return r


def sil():
    cmd = [sys.executable, "-B", str(RIFLE / "rifle_silhouette.py"), "--npz", str(RR_NPZ), "--stage",
           f"detail/{PART}/sil", "--json", str(WORK / "sil.json")]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    r = json.loads((WORK / "sil.json").read_text())
    return r


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if "--blender-build" in argv:
        blender_build()
    else:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd", choices=["iter", "b3", "sil", "build", "measure"])
        ap.add_argument("--tag", default="r1")
        ap.add_argument("--no-build", action="store_true")
        ap.add_argument("--no-render", action="store_true")
        a = ap.parse_args(argv)
        if a.cmd == "iter":
            iterate(a.tag, not a.no_build, not a.no_render)
        elif a.cmd == "build":
            print(json.dumps(build(), indent=1)[:3000])
        elif a.cmd == "b3":
            b3()
        elif a.cmd == "measure":
            measure()
        else:
            r = sil()
            print(json.dumps(r, indent=1)[:200])
