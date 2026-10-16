"""(R2) rim-slab probe: build only the edited parts (chassis, butt, butt pad, riser, grip), report UD / manifold /
ring checks, and render Workbench close-ups of the round-1 worst spots (grip base, forend nose, stock / riser, chassis
underside). Headless:
    blender -b --factory-startup --python Scripts/guns/sniper/sr_rim_probe.py -- <out_dir> [parts,comma,list]
"""
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sr_common  # noqa: E402,F401
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from gunlib import bl  # noqa: E402
import numpy as np  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(argv[0] if argv else "WorkFiles/guns/sniper/scratch/r2/probe").resolve()
OUT.mkdir(parents=True, exist_ok=True)
ONLY = set((argv[1] if len(argv) > 1 else "chassis,butt,butt_pad,cheek_riser,grip").split(","))

bl.reset_scene()
import sniper_parts as SP  # noqa: E402
t0 = time.time()
res = SP.build_all(only=ONLY)
print("built in %.1fs" % (time.time() - t0))
(OUT / "probe_report.json").write_text(json.dumps(res, indent=1, default=str))
for k, v in res.items():
    print("PART", k, json.dumps({"tris": v.get("triangles"), "shells": v.get("shells"), "boundary": v.get("boundary_edges"),
                                 "multi": v.get("multi_face_edges"), "ud": v.get("ud"),
                                 "rings": {s: d.get("rings_simple") for s, d in (v.get("rim_slab") or {}).items()},
                                 "err": v.get("error")}, default=str))

# ---- where the UD drops sit (5 mm clusters, frame M)
from gunlib import ud as _ud  # noqa: E402
for name in ONLY:
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    V, T = bl.tris_np(ob, offset_mm=tuple(np.asarray(sr_common.GRIP, float)))
    if not len(T):
        continue
    area, L, hgt, drop, _c = _ud._tri_metrics(V, T)
    bad = drop | (area < _ud.MIN_AREA_MM2) | (L.min(1) < _ud.MIN_EDGE_MM) | (hgt < _ud.MIN_HEIGHT_MM)
    if bad.any():
        C = V[T[bad]].mean(1)
        keys, cnt = np.unique(np.round(C / 5.0) * 5.0, axis=0, return_counts=True)
        order = np.argsort(-cnt)[:12]
        import sr_rimslab as RS
        print("NMLOC", name, RS.nonmanifold_locate(ob, np.asarray(sr_common.GRIP, float)))
        print("UDLOC", name, int(bad.sum()), [(keys[i].tolist(), int(cnt[i])) for i in order])

# ---- renders (Workbench, studio light, cavity off; frame M -> object space: (mm - GRIP) / 1000)
G0 = np.asarray(sr_common.GRIP, float)
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"
sh.color_type = "SINGLE"
sh.single_color = (0.33, 0.36, 0.28)
sh.show_specular_highlight = True
sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
sc.world = bpy.data.worlds.new("w") if sc.world is None else sc.world


def M(p):
    return Vector(((p[0] - G0[0]) / 1000.0, (p[1] - G0[1]) / 1000.0, (p[2] - G0[2]) / 1000.0))


def shot(name, target, eye, lens=50.0, ortho=None):
    cam = bpy.data.objects.get("pcam") or bpy.data.objects.new("pcam", bpy.data.cameras.new("pcam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.location = M(eye)
    d = M(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    cam.data.clip_start = 0.001
    if ortho:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho / 1000.0
    else:
        cam.data.type = "PERSP"
    sc.camera = cam
    sc.render.filepath = str(OUT / (name + ".png"))
    bpy.ops.render.render(write_still=True)


# round-1 judge spots (frame M, mm; +Y = gun left, the right side is -Y)
shot("grip_base_r34", (280, 0, -150), (380, -170, -230), lens=60)
shot("grip_right", (280, 0, -110), (280, -400, -110), ortho=150)
shot("forend_nose", (820, 0, -30), (930, -150, -110), lens=60)
shot("chassis_under", (520, 0, -50), (560, -260, -200), lens=45)
shot("stock_r34", (140, 0, -40), (40, -330, 60), lens=40)
shot("stock_right", (150, 0, -60), (150, -500, -60), ortho=260)
shot("riser_low", (130, 0, 0), (200, -200, -60), lens=50)
shot("pad_top", (25, 0, 10), (-90, -140, 90), lens=60)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "probe.blend"))
print("PROBE_DONE")
