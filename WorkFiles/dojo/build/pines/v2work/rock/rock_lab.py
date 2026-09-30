"""Rock v3 lab: dense SDF rock only, SG14 / SG15 numbers, clay renders (workbench) + trace overlays.

blender -b --factory-startup --python rock_lab.py -- --variants PineD1,PineD2 --out <dir>
"""
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
for p in (ROOT / "Scripts", ROOT / "Scripts" / "vegetation", ROOT / "Scripts" / "dojo" / "pines"):
    sys.path.insert(0, str(p))
import rock_sdf as rs  # noqa: E402
import rock_v3  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
import argparse  # noqa: E402
ap = argparse.ArgumentParser()
ap.add_argument("--variants", default="PineD1,PineD2")
ap.add_argument("--out", required=True)
ap.add_argument("--res", type=int, default=700)
a = ap.parse_args(argv)
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=True)
SPEC = json.loads((ROOT / "Scripts/dojo/pines/pines_spec.json").read_text())

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
coll = sc.collection
res = {}
for v in a.variants.split(","):
    t0 = time.time()
    D = rock_v3.build_dense(v)
    V, F = D["V"], D["F"]
    k = 1.0  # the spec outlines are already x0.65 (make_spec d_rock_v3)
    fr = np.asarray(SPEC[v]["rock"]["front_xz"]) * k
    sd = np.asarray(SPEC[v]["rock"]["side_yz"]) * k
    Vg = V[V[:, 2] >= 0.0]
    above = (V[F][:, :, 2] >= -0.001).all(1)
    iou_f, Af, Bf = rs.rasterise_iou(V[V[:, 2] >= 0], fr, (0, 2))
    iou_s, As, Bs = rs.rasterise_iou(V[V[:, 2] >= 0], sd, (1, 2))
    np.savez_compressed(out / f"{v}_sil.npz", Af=Af, Bf=Bf, As=As, Bs=Bs)
    r = {"iou_front": round(iou_f, 3), "iou_side": round(iou_s, 3),
         "bbox": [np.round(V.min(0), 3).tolist(), np.round(V.max(0), 3).tolist()],
         "trace_bbox_front": [np.round(fr.min(0), 3).tolist(), np.round(fr.max(0), 3).tolist()],
         "plane_fraction": round(rock_v3.plane_fraction(V, F, D["lobe_pl"]), 3),
         "sharp_crease_share": round(rock_v3.sharp_crease_share(V, F), 4),
         "tris": int(len(F)), "info": D["info"], "s": round(time.time() - t0, 1)}
    bt = np.asarray(SPEC[v]["trunk"]["pts"][0]) * k
    r0 = SPEC[v]["trunk"]["min_r"][0]
    ring = np.linalg.norm(V[:, :2] - bt[:2], axis=1)
    r["top_under_base"] = {f"{f:.1f}r": round(float(V[ring < f * r0, 2].max()), 4) for f in (0.3, 0.8, 1.2)}
    r["base_xy_scaled"] = np.round(bt[:2], 4).tolist()
    np.savez_compressed(out / f"{v}_dense.npz", V=V.astype(np.float32), F=F.astype(np.int32))
    res[v] = r
    print(v, json.dumps(r), flush=True)
    ob = rock_v3.make_obj(f"rock_{v}", V, F, coll)
    ob["variant"] = v
json.dump(res, open(out / "lab.json", "w"), indent=1)

# clay renders
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"
sh.color_type = "SINGLE"
sh.single_color = (0.6, 0.6, 0.58)
sh.show_cavity = True
sh.cavity_type = "BOTH"
sh.show_shadows = True
sc.display.shadow_focus = 0.2
sc.render.resolution_x = a.res
sc.render.resolution_y = a.res
sc.render.film_transparent = False
w = bpy.data.worlds.new("w")
sc.world = w
cam_d = bpy.data.cameras.new("cam")
cam_d.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_d)
coll.objects.link(cam)
sc.camera = cam
for ob in [o for o in bpy.data.objects if o.name.startswith("rock_")]:
    for o in bpy.data.objects:
        if o.name.startswith("rock_"):
            o.hide_render = o is not ob
    v = ob["variant"]
    for view, az in (("front", 0.0), ("side", 90.0), ("3q", 45.0), ("top", None)):
        cam_d.ortho_scale = 1.9
        if az is None:
            cam.location = (0, 0, 6)
            cam.rotation_euler = (0, 0, 0)
        else:
            ar = math.radians(az)
            # front: camera on -Y looking +Y; side: camera on +X looking -X
            cam.location = (6 * math.sin(ar), -6 * math.cos(ar), 0.55)
            cam.rotation_euler = (math.radians(90), 0, ar)
        sc.render.filepath = str(out / f"{v}_{view}_clay.png")
        bpy.ops.render.render(write_still=True)
print("done", flush=True)
