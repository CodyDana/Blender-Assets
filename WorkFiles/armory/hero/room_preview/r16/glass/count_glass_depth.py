"""glass-bug: count the transparent (glass) faces a camera ray crosses before it reaches an opaque surface, for every
layout camera, on a grid of rays. Read only (never saves). Args after --: --layout PATH [--res WxH] [--step N] [--out JSON]"""
import bpy, json, math, sys
from mathutils import Vector
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(n, d):
    return ARGS[ARGS.index(n) + 1] if n in ARGS else d
data = json.load(open(arg("--layout", ""), encoding="utf-8"))
W, H = (int(v) for v in arg("--res", "1448x1086").split("x"))
step = int(arg("--step", "4"))
sc = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()

def is_transparent(obj, index):
    me = obj.data
    try:
        poly = me.polygons[index]
        m = obj.material_slots[poly.material_index].material
    except Exception:
        return False, None
    if m is None or not m.node_tree:
        return False, None
    if any(n.type == "BSDF_TRANSPARENT" for n in m.node_tree.nodes) and "Glass" in m.name:
        return True, m.name
    return False, m.name

out = {}
for c in data["cameras"]:
    loc = Vector(c["loc"]); d = Vector(c["look_at"]) - loc
    q = d.to_track_quat("-Z", "Y")
    R = q.to_matrix()
    lens, sw = c["lens_mm"], 36.0
    shift_y = c.get("shift_y", 0.0)
    # sensor fit AUTO: the larger dimension spans sensor_width
    if W >= H:
        sx, sy = sw, sw * H / W
    else:
        sx, sy = sw * W / H, sw
    hist, worst = {}, (0, None)
    for py in range(0, H, step):
        for px in range(0, W, step):
            u = ((px + 0.5) / W - 0.5) * sx
            v = (0.5 - (py + 0.5) / H) * sy + shift_y * max(sx, sy)
            ray = (R @ Vector((u, v, -lens))).normalized()
            o = loc.copy(); n = 0; mats = []
            for _ in range(80):
                hit, p, nrm, idx, obj, _m = sc.ray_cast(dg, o, ray)
                if not hit:
                    break
                tr, mn = is_transparent(obj.original if hasattr(obj, "original") else obj, idx)
                if not tr:
                    break
                n += 1; mats.append(mn)
                o = p + ray * 1e-4
            hist[n] = hist.get(n, 0) + 1
            if n > worst[0]:
                worst = (n, (px, py), sorted(set(mats)))
    out[c["name"]] = {"hist": dict(sorted(hist.items())), "worst": worst,
                      "over8_px_frac": sum(v for k, v in hist.items() if k > 8) / sum(hist.values())}
    print("DEPTH", c["name"], json.dumps(out[c["name"]]), flush=True)
json.dump(out, open(arg("--out", "depth.json"), "w"), indent=1)
