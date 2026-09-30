"""Project the built case instances (plinth + glass meshes, every vertex) and the rear keep-clear pieces through the
C1 camera at 1448 x 1086; write c1_boxes.json beside the blend. Run: blender -b <blend> --python c1_boxes.py -- <layout.json>"""
import json, sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

lay = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text())
cam = next(c for c in lay["cameras"] if c["name"] == "C1_EntryReveal")
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 1448, 1086
cd = bpy.data.cameras.new("C1"); cd.lens = cam["lens_mm"]; cd.shift_y = cam.get("shift_y", 0.0); cd.sensor_width = 36.0
co = bpy.data.objects.new("C1", cd); sc.collection.objects.link(co)
co.location = cam["loc"]
co.rotation_euler = (Vector(cam["look_at"]) - Vector(cam["loc"])).to_track_quat("-Z", "Y").to_euler()
sc.camera = co
bpy.context.view_layer.update()
W, H = 1448, 1086

def proj(objs):
    xs, ys = [], []
    for o in objs:
        for v in o.data.vertices:
            p = world_to_camera_view(sc, co, o.matrix_world @ v.co)
            xs.append(p.x * W); ys.append((1 - p.y) * H)
    return [min(xs), max(xs), min(ys), max(ys)]

insts = [o for o in bpy.data.collections["Assembly"].objects]
labels = {}
for c in lay["cases"]:
    if c["type"] == "Hero":
        continue
    x, y = c["loc"]
    objs = [o for o in insts if o.name.split("__")[0] in (f"SM_AK_Case_{c['type']}_Plinth", f"SM_AK_Case_{c['type']}_Glass")
            and abs(o.matrix_world.translation.x - x) < 1e-3 and abs(o.matrix_world.translation.y - y) < 1e-3]
    b = proj(objs)
    labels[c["label"]] = {"type": c["type"], "loc": [x, y], "n_meshes": len(objs), "raw": [round(v, 1) for v in b],
                          "box": [round(max(40, b[0])), round(min(1408, b[1])), round(b[2]), round(b[3])]}
keep = {}
for key, piece, side in (("foot_lantern", ("SM_AK_Lantern_S", "SM_AK_H_LanternStand"), None),
                         ("deck_lantern", ("SM_AK_Lantern_M",), None),
                         ("corner_niche", ("SM_AK_H_CornerNiche_W", "SM_AK_H_CornerNiche_E"), None),
                         ("rear_alcove", ("SM_AK_RearAlcove",), None)):
    objs = [o for o in insts if o.name.split("__")[0] in piece]
    for o in objs:
        s = "W" if o.matrix_world.translation.x < 6 else "E"
        keep.setdefault(f"{key}_{s}", []).append(o)
keep = {k: [round(v) for v in proj(v)] for k, v in keep.items()}

def gap(a, b):
    return max(a[0] - b[1], b[0] - a[1], a[2] - b[3], b[2] - a[3])

pairs = []
L = list(labels)
for i, a in enumerate(L):
    for b in L[i + 1:]:
        pairs.append({"pair": [a, b], "gap_px": round(gap(labels[a]["box"], labels[b]["box"]), 1)})
kc = []
for a in L:
    for k, kb in keep.items():
        kc.append({"case": a, "keep": k, "gap_px": round(gap(labels[a]["box"], kb), 1)})
out = {"camera": cam, "res": [W, H], "visible_x": [40, 1408], "cases": labels, "keep_clear_mesh_boxes": keep,
       "pairs": sorted(pairs, key=lambda p: p["gap_px"]), "keep_clear": sorted(kc, key=lambda p: p["gap_px"])[:16]}
dst = Path(bpy.data.filepath).parent / "c1_boxes.json"
dst.write_text(json.dumps(out, indent=1))
print("C1BOXES", json.dumps({k: v["box"] for k, v in labels.items()}))
print("PAIRS", json.dumps(out["pairs"][:14]))
print("KEEP", json.dumps(out["keep_clear"][:10]))
print("KEEPBOX", json.dumps(keep))
