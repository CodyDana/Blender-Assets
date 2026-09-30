"""CLIMB check: every spec 5.1 climb route replayed through GASP's own traversal logic, geometrically, on the grey-box.

GASP's rules and numbers are the ones read from the sample's assets (WorkFiles/dojo/build/GASP_TRAVERSAL.md):
 1 forward trace: capsule radius 30, half height 60 (on the ground), from the capsule centre along the facing for 75 cm
   (standing; 75-350 cm with speed 0-500), Traversable channel -> must hit a LevelBlock_Traversable (our markers); the
   sweep stops at the FIRST marker it reaches among ALL markers (start-penetrating = distance 0), and a route passes
   only if that first marker is the route's own (2026-09-28 round 2: the plinth stance started inside the pad marker)
 2 ledges: the marker's four top edges, outward normals; the ledge closest to the actor; it must be >= 60 cm long; the
   front point = the point on it closest to the hit, clamped 30 cm from its ends; the back point = the closest point on
   the opposite ledge
 3 room check: capsule (radius 30, half height 86) sweep, Visibility channel, from the actor to front + normal * 32 +
   (0, 0, 88): must be clear
 4 obstacle height = front ledge z - capsule bottom z
 5 top sweep: front room point -> back room point (back + back normal * 32 + (0, 0, 88)), Visibility: a hit invalidates
   the back ledge and the depth becomes the XY distance front ledge -> impact; otherwise depth = front -> back ledge
 6 back floor: sweep down from the back room point to back + normal * 32 - (0, 0, 50); a hit = back floor, back ledge
   height = back ledge z - floor z
 7 CHT_TraversalMontages_CMC root rows (in order): Hurdle (front, back, floor, depth <= 59, back ledge height >= 50);
   Mantle (front, back, floor, depth <= 59, back ledge height <= 10); Vault (front, back, NO floor, depth <= 59);
   Mantle (front, depth >= 59); then the nested table (ground rows): Hurdle height <= 125 and depth <= 60; Mantle height
   <= 150 (1 m set) or 150-275 (2.5 m climb set); Vault height <= 125 and depth <= 60
Visibility-blocking hulls = the UCX hulls of every class whose layout.json visibility response is block (the same hulls
Unreal imports). Capsules are tested as spheres along the axis every 5 cm against a BVH of the hulls (exact surface
distance, inside test by the outward normal). Walk entries (walk_to) are checked against the CMC step height 0.45 m.
"SPEC" entries replay the spec as written (no landing, AC top +4.75) with the landing hulls removed.

Run: blender -b --factory-startup Assets/Dojo/DojoGreybox.blend --python Scripts/dojo/climb_check.py
Result: WorkFiles/dojo/build/climb_check.json
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
import sys  # noqa: E402
_A = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
# optional: -- --layout <file in WorkFiles/dojo/build> --out <path relative to WorkFiles/dojo/build> (KIT 1 reruns)
LAYOUT_NAME = _A[_A.index("--layout") + 1] if "--layout" in _A else "layout.json"
OUT_NAME = _A[_A.index("--out") + 1] if "--out" in _A else "climb_check.json"
# optional: -- --hover <m>: rest the capsule this far above its floor, as UE's CharacterMovement does (MIN_FLOOR_DIST
# 1.9 cm .. MAX_FLOOR_DIST 2.4 cm). Default 0 (the grey-box / kit-1 runs). The showcase run passes 0.019: on the ground
# kit's irregular board / bed hulls a capsule set down in 2 mm steps can otherwise start its room sweep in contact.
HOVER = float(_A[_A.index("--hover") + 1]) if "--hover" in _A else 0.0
L = json.loads((WORK / LAYOUT_NAME).read_text(encoding="utf-8"))
# GASP numbers (GASP_TRAVERSAL.md: SandboxCharacter_CMC CDO, GetTraversalCheckInputs, AC_TraversalLogic, the chooser)
R, HH = 0.30, 0.86                  # capsule radius / half height
TR_R, TR_HH, TR_DIST = 0.30, 0.60, 0.75
ROOM_OUT, ROOM_UP, FLOOR_DOWN = 0.32, 0.88, 0.50
MIN_LEDGE = 0.60
STEP = 0.45
cls_of = {p: v["class"] for p, v in L["pieces"].items()}
kit = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}


def hull_polys(pred):
    verts, polys = [], []
    for inst in bpy.data.collections["Assembly"].objects:
        piece = inst.name.split("__")[0]
        if piece not in kit or not pred(cls_of[piece]):
            continue
        for h in kit[piece].children:
            if not h.name.startswith("UCX_"):
                continue
            bm = bmesh.new()
            bm.from_mesh(h.data)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            mw = inst.matrix_world @ h.matrix_local
            base = len(verts)
            verts += [mw @ v.co for v in bm.verts]
            polys += [[base + v.index for v in f.verts] for f in bm.faces]
            bm.free()
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0)


vis_block = lambda c: L["collision_classes"][c]["visibility"] == "block"   # noqa: E731
pawn_block = lambda c: L["collision_classes"][c]["pawn"] == "block"        # noqa: E731
BVH = {"vis": hull_polys(vis_block), "pawn": hull_polys(pawn_block)}


def bvh_without(kind, excluded):
    key = (kind, tuple(sorted(excluded)))
    if key not in BVH:
        base = vis_block if kind == "vis" else pawn_block
        BVH[key] = hull_polys(lambda c: base(c) and c not in excluded)
    return BVH[key]


def sphere_hits(bvh, p, r):
    """Contact when the sphere centre is within r of a hull surface. No inside test: every sweep starts outside the
    hulls and moves in 1 cm steps, so a centre cannot get deeper than r without a sample first touching the surface
    (and a nearest-face normal at a hull edge is not a reliable inside test)."""
    hit = bvh.find_nearest(p, r)
    return hit[0] if hit[0] is not None and hit[3] < r else None


def capsule_hits(bvh, c, r, hh):
    a = max(hh - r, 0.0)
    n = max(1, int(math.ceil(2 * a / 0.05)))
    for i in range(n + 1):
        p = c + Vector((0, 0, -a + 2 * a * i / n))
        loc = sphere_hits(bvh, p, r)
        if loc is not None:
            return loc
    return None


def sweep(bvh, a, b, r, hh, step=0.01):
    """First blocking impact of a capsule moving from a to b (None = clear). Returns (impact point, travel fraction)."""
    d = (b - a).length
    n = max(1, int(math.ceil(d / step)))
    for i in range(n + 1):
        c = a.lerp(b, i / n)
        loc = capsule_hits(bvh, c, r, hh)
        if loc is not None:
            return loc, i / n
    return None


def rest_centre(bvh, x, y, floor):
    """The capsule centre height where the capsule rests at (x, y): its bottom sphere is lowered from 25 cm above the
    floor until it touches a surface (on a slope the capsule sits a little above it); no contact = the given floor."""
    z = floor + HH + 0.25
    while z > floor + HH - 0.05:
        if sphere_hits(bvh, Vector((x, y, z - 0.002 - (HH - R))), R) is not None:
            return z + HOVER
        z -= 0.002
    return floor + HH + HOVER


def box_dist_seg(box, c, a, r):
    """Distance from a vertical segment (centre c, half length a) to an axis-aligned box."""
    x0, x1, y0, y1, z0, z1 = box
    dx = max(x0 - c.x, 0.0, c.x - x1)
    dy = max(y0 - c.y, 0.0, c.y - y1)
    dz = max(z0 - (c.z + a), 0.0, (c.z - a) - z1)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def ledges(box):
    x0, x1, y0, y1, _z0, z = box
    return {"L1": (Vector((x0, y0, z)), Vector((x1, y0, z)), Vector((0, -1, 0))),
            "L2": (Vector((x0, y1, z)), Vector((x1, y1, z)), Vector((0, 1, 0))),
            "L3": (Vector((x0, y0, z)), Vector((x0, y1, z)), Vector((-1, 0, 0))),
            "L4": (Vector((x1, y0, z)), Vector((x1, y1, z)), Vector((1, 0, 0)))}


OPP = {"L1": "L2", "L2": "L1", "L3": "L4", "L4": "L3"}


def closest_on(seg, p, clamp=0.0):
    a, b, _n = seg
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    if clamp:
        L_ = ab.length
        t = max(clamp / L_, min(1.0 - clamp / L_, t))
    return a + ab * t


def chooser(front, back, floor, depth_cm, blh_cm, h_cm):
    root = None
    if front and back and floor and depth_cm <= 59 and blh_cm >= 50:
        root = "Hurdle"
    elif front and back and floor and depth_cm <= 59 and blh_cm <= 10:
        root = "Mantle"
    elif front and back and not floor and depth_cm <= 59:
        root = "Vault"
    elif front and depth_cm >= 59:
        root = "Mantle"
    if root is None:
        return None, "no root chooser row matches (depth %.0f cm, back ledge %s, back floor %s, back ledge height %s)" % (
            depth_cm, back, floor, None if blh_cm is None else round(blh_cm))
    if root == "Hurdle":
        ok = h_cm <= 125 and depth_cm <= 60
        return ("Hurdle" if ok else None), ("hurdle rows: height <= 125, depth <= 60" + ("" if ok else " FAIL"))
    if root == "Vault":
        ok = h_cm <= 125 and depth_cm <= 60
        return ("Vault" if ok else None), ("vault rows: height <= 125, depth <= 60" + ("" if ok else " FAIL"))
    if h_cm <= 150:
        return "Mantle (1 m set, height <= 150)", "mantle rows 0-5"
    if h_cm <= 275:
        return "Mantle (2.5 m climb set, 150-275)", "mantle rows 6-11"
    return None, "mantle rows: height %.0f > 275" % h_cm


def check(rt):
    excl = rt.get("exclude_class") or []
    vis = bvh_without("vis", excl) if excl else BVH["vis"]
    pawn = bvh_without("pawn", excl) if excl else BVH["pawn"]
    x, y = rt["stance"]
    zc = rest_centre(pawn, x, y, rt["floor_z"])
    A = Vector((x, y, zc))
    feet = zc - HH
    out = {"route": rt["route"], "step": rt["step"], "stance": [x, y], "floor_z": rt["floor_z"],
           "capsule_centre_z": round(zc, 3), "feet_z": round(feet, 3)}
    if rt.get("walk_to") is not None and not rt.get("marker") and not rt.get("virtual_marker"):
        rise = rt["walk_to"] - rt["floor_z"]
        out.update({"kind": "walk", "rise_m": round(rise, 3), "step_limit_m": STEP,
                    "works": rise <= STEP, "why": "CMC step-up" if rise <= STEP else "rise over the 0.45 m step height"})
        if rise < 0:
            out["why"] = "drop (walk off)"
            out["works"] = True
        return out
    if rt.get("walk_to") is not None:
        out["rise_m"] = round(rt["walk_to"] - rt["floor_z"], 3)
        out["walkable_step"] = out["rise_m"] <= STEP
    face = Vector((rt["face"][0], rt["face"][1], 0.0))
    # 1 forward trace (Traversable): GASP's capsule sweep stops at the FIRST LevelBlock_Traversable it reaches, whichever
    # marker that is (a start-penetrating overlap counts as a hit at distance 0), so every marker is tested, not only the
    # route's own; a route whose sweep reaches another marker first fails (in-engine it would traverse that block)
    if rt.get("virtual_marker"):
        cands = [("(virtual)", rt["virtual_marker"])]
    else:
        cands = [(m["name"], m["box"]) for m in L["traversal_markers"]]
    hit, hit_name, box, first_at = None, None, None, []
    n = int(TR_DIST / 0.01)
    for i in range(n + 1):
        c = A + face * (TR_DIST * i / n)
        first_at = [(nm, bx) for nm, bx in cands if box_dist_seg(bx, c, TR_HH - TR_R, TR_R) <= TR_R]
        if first_at:
            hit_name, box = min(first_at, key=lambda t: box_dist_seg(t[1], c, 0.0, 0.0))
            x0, x1, y0, y1, z0, z1 = box
            hit = Vector((min(max(c.x, x0), x1), min(max(c.y, y0), y1), min(max(c.z, z0), z1)))
            out["forward_trace_start_penetrating"] = i == 0
            break
    out["forward_trace_hit"] = None if hit is None else [round(v, 3) for v in hit]
    out["forward_trace_marker"] = hit_name
    if len(first_at) > 1:
        out["forward_trace_also_touching"] = sorted(nm for nm, _b in first_at if nm != hit_name)
    if hit is None:
        out.update({"kind": "traversal", "works": False, "why": "forward trace finds no traversable block"})
        return out
    if not rt.get("virtual_marker") and (hit_name != rt["marker"] or len(first_at) > 1):
        out.update({"kind": "traversal", "works": False,
                    "why": f"forward trace reaches marker {sorted(nm for nm, _b in first_at)} first, not only "
                           f"{rt['marker']}" + (" (start-penetrating)" if out["forward_trace_start_penetrating"] else "")})
        return out
    # 2 ledges
    L4 = ledges(box)
    key = min(L4, key=lambda k: (closest_on(L4[k], A) - A).length)
    seg = L4[key]
    length = (seg[1] - seg[0]).length
    if length < MIN_LEDGE:
        out.update({"kind": "traversal", "works": False, "why": f"ledge {length:.2f} m < 0.60"})
        return out
    F, nF = closest_on(seg, hit, clamp=MIN_LEDGE / 2), seg[2]
    B, nB = closest_on(L4[OPP[key]], F), L4[OPP[key]][2]
    Rf = F + nF * ROOM_OUT + Vector((0, 0, ROOM_UP))
    Rb = B + nB * ROOM_OUT + Vector((0, 0, ROOM_UP))
    h = F.z - feet
    out.update({"kind": "traversal", "ledge": key, "front_ledge": [round(v, 3) for v in F],
                "back_ledge": [round(v, 3) for v in B], "obstacle_height_cm": round(h * 100, 1)})
    # 3 room check
    room = sweep(vis, A, Rf, R, HH)
    out["room_check_clear"] = room is None
    if room is not None:
        out.update({"works": False, "why": f"no room to move up to the ledge (hit at {[round(v, 2) for v in room[0]]})"})
        return out
    # 5 top sweep
    top = sweep(vis, Rf, Rb, R, HH)
    back = top is None
    if back:
        depth = (Vector((F.x, F.y)) - Vector((B.x, B.y))).length
    else:
        depth = (Vector((F.x, F.y)) - Vector((top[0].x, top[0].y))).length
        out["top_sweep_impact"] = [round(v, 3) for v in top[0]]
    out["has_back_ledge"], out["obstacle_depth_cm"] = back, round(depth * 100, 1)
    # 6 back floor
    floor, blh = False, None
    if back:
        fl = sweep(vis, Rb, B + nB * ROOM_OUT - Vector((0, 0, FLOOR_DOWN)), R, HH)
        if fl is not None:
            floor, blh = True, (B.z - fl[0].z) * 100
    out["has_back_floor"], out["back_ledge_height_cm"] = floor, None if blh is None else round(blh, 1)
    action, why = chooser(True, back, floor, depth * 100, blh if blh is not None else 0.0, h * 100)
    out["action"], out["why"], out["works"] = action, why, action is not None
    # after a mantle the capsule must fit standing on top, just inside the front ledge
    if action and action.startswith("Mantle"):
        top_c = F - nF * (R + 0.10) + Vector((0, 0, HH + 0.03))
        out["stand_on_top_clear"] = capsule_hits(pawn, top_c, R, HH) is None
        out["works"] = out["works"] and out["stand_on_top_clear"]
        if not out["stand_on_top_clear"]:
            out["why"] += "; no standing room on top"
    return out


res = {"hover_m": HOVER, "gasp": {"capsule_r_m": R, "capsule_half_height_m": HH, "trace_r_m": TR_R, "trace_half_height_m": TR_HH,
                "trace_distance_standing_m": TR_DIST, "min_ledge_m": MIN_LEDGE, "step_m": STEP},
       "routes": [check(rt) for rt in L["climb_routes"]]}
by_route = {}
for r in res["routes"]:
    if r["route"].endswith("spec"):
        continue
    by_route.setdefault(r["route"], []).append(r["works"])
res["route_verdicts"] = {k: all(v) for k, v in by_route.items()}
res["spec_as_written"] = {r["route"]: {"works": r["works"], "why": r.get("why"), "depth_cm": r.get("obstacle_depth_cm"),
                                       "height_cm": r.get("obstacle_height_cm"), "rise_m": r.get("rise_m")}
                          for r in res["routes"] if r["route"].endswith("spec")}
res["passed"] = all(res["route_verdicts"].values())
(WORK / OUT_NAME).write_text(json.dumps(res, indent=1), encoding="utf-8")
for r in res["routes"]:
    print("CLIMB", r["route"], r["step"], "|", r.get("action") or r.get("kind"), "| works", r["works"], "|",
          "h", r.get("obstacle_height_cm"), "d", r.get("obstacle_depth_cm"), "rise", r.get("rise_m"), "|", r.get("why"))
print("CLIMB_VERDICTS", json.dumps(res["route_verdicts"]), "passed", res["passed"])
