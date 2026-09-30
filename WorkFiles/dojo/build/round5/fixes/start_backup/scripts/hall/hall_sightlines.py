"""Hall sightlines: can a player see INTO the closed hall anywhere? Rays are cast against the hall's RENDER meshes (every
SM_DKH_* instance in DojoHall.blend's Assembly, context pieces left out) and a ray "leaks" when it enters the hall's
interior volume before it hits anything. The interior is a convex volume: the body shrunk 0.25 m inside the wall
lines, from 5 cm over the floor up to 0.16 m under the upper roof's four planes (the rafter bays and the roof void count; nothing above the tiles does).

Test A, the wall heads (the measurer's slot between the nageshi and the kamoi, and the module seams): eyes 0.4 / 0.7 /
  1.0 m in front of every wall, every 0.5 m along it, at +1.04 / 1.3 / 1.58 / 1.9 / 2.2 / 2.5 (horizontal rays at the panel rails' heights too); a fan of 13 x 13 directions toward the
  wall (azimuth -60..60, elevation -30..60 deg).
Test B, the upper eave (the open rafter bays over the wall plates): eyes in the courtyard (Y 12-18, +1.6..+3.0), on the
  lower roofs (eye +5.1), in the side yards and the rear alley, each aimed at targets every 0.15 m along every wall line
  at +5.63 / +5.68 / +5.73 / +5.78 (between the wall-plate top and the sarking).

Run: blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/hall/hall_sightlines.py
Out: WorkFiles/dojo/build/hall/sightlines_hall.json (0 leaks = pass)
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(bpy.data.filepath).resolve().parents[2]
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "hall" / "sightlines_hall.json"
BX0, BX1, BY0, BY1 = 13.0, 31.0, 24.0, 34.0
WALL = 0.12                       # post half width: the outer wall face
UP = dict(x0=12.1, x1=31.9, y0=23.1, y1=34.9, z=5.5, tn=math.tan(math.radians(25.0)))
IN = 0.25


def build_bvh():
    verts, polys = [], []
    dg = bpy.context.evaluated_depsgraph_get()
    n = 0
    for o in bpy.data.collections["Assembly"].objects:
        if not o.name.startswith("SM_DKH_") or o.type != "MESH":
            continue
        me = o.evaluated_get(dg).to_mesh()
        mw = o.matrix_world
        base = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        polys += [[base + i for i in p.vertices] for p in me.polygons]
        o.evaluated_get(dg).to_mesh_clear()
        n += 1
    print("SIGHT bvh instances", n, "tris-ish", len(polys), flush=True)
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0)


# interior: half-spaces  n . p <= d
HS = [((-1, 0, 0), -(BX0 + WALL + IN)), ((1, 0, 0), BX1 - WALL - IN), ((0, -1, 0), -(BY0 + WALL + IN)),
      ((0, 1, 0), BY1 - WALL - IN), ((0, 0, -1), -0.55)]
# under the four upper-roof planes minus 0.35 (front: z <= z + (y - y0) tn - 0.35, etc.)
t = UP["tn"]
Zc = UP["z"] - 0.16
HS += [((0, -t, 1), Zc - t * UP["y0"]),        # front plane  z <= Z + (y - y0) t - 0.35
       ((0, t, 1), Zc + t * UP["y1"]),         # back plane   z <= Z + (y1 - y) t - 0.35
       ((-t, 0, 1), Zc - t * UP["x0"]),        # west plane   z <= Z + (x - x0) t - 0.35
       ((t, 0, 1), Zc + t * UP["x1"])]         # east plane   z <= Z + (x1 - x) t - 0.35
HS = [(Vector(n), d) for n, d in HS]
# round 3: the raised centre plane (X 17-27 between the diagonal ridges) lifts the roof void over the front centre, so
# the interior gets a second convex volume there: under the centre plane minus 0.16, inside the two diagonals' vertical
# planes (numbers from layout_hall.json)
_LH = json.loads((ROOT / "WorkFiles" / "dojo" / "build" / "hall" / "layout_hall.json").read_text(encoding="utf-8"))
_FR = _LH["numbers"]["upper_roof"].get("front_recess") or {}
VOLS = [HS]
if _FR.get("mode") == "raised centre plane":
    yR, zc = _FR["centre_eave_y"], _FR["centre_eave_z"]
    tc = math.tan(math.radians(_FR["centre_plane_pitch_deg"]))
    HC = HS[:5] + HS[6:]                            # all but the front plane (index 5)
    HC.append((Vector((0, -tc, 1)), zc - tc * yR - 0.16))
    for key in ("diagonal_left", "diagonal_right"):
        (_, _), (x1, y1), (x0, y0) = _FR[key]
        dd = Vector((x0 - x1, y0 - y1, 0)).normalized()
        nrm = Vector((-dd.y, dd.x, 0))              # keep the centre side: n . p <= d with n pointing away from it
        if nrm.x * (22.0 - x1) > 0:
            nrm = -nrm
        HC.append((nrm, nrm.dot(Vector((x1, y1, 0)))))
    VOLS.append(HC)


def enter_interval(o, dvec):
    """The earliest entry into any interior volume (None if the ray misses them all)."""
    best = None
    for hs in VOLS:
        iv = enter_interval_one(o, dvec, hs)
        if iv is not None and (best is None or iv[0] < best[0]):
            best = iv
    return best


def enter_interval_one(o, dvec, hs):
    """Cyrus-Beck: the ray's [t0, t1] inside one convex interior volume (None if it misses)."""
    t0, t1 = 0.0, 1e9
    for n, d in hs:
        den = n.dot(dvec)
        num = d - n.dot(o)
        if abs(den) < 1e-12:
            if num < 0:
                return None
            continue
        tt = num / den
        if den > 0:
            t1 = min(t1, tt)
        else:
            t0 = max(t0, tt)
        if t0 > t1:
            return None
    return t0, t1


def leaks(bvh, o, dvec, maxd=40.0):
    iv = enter_interval(o, dvec)
    if iv is None or iv[0] > maxd:
        return False
    hit = bvh.ray_cast(o, dvec, maxd)
    th = hit[3] if hit[0] is not None else 1e9
    return iv[0] + 1e-4 < th


def walls():
    """(name, point on the outer face, outward normal, along unit, length)"""
    return [("front", Vector((BX0, BY0 - WALL, 0)), Vector((0, -1, 0)), Vector((1, 0, 0)), BX1 - BX0),
            ("back", Vector((BX0, BY1 + WALL, 0)), Vector((0, 1, 0)), Vector((1, 0, 0)), BX1 - BX0),
            ("west", Vector((BX0 - WALL, BY0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), BY1 - BY0),
            ("east", Vector((BX1 + WALL, BY0, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)), BY1 - BY0)]


def test_a(bvh):
    res = {}
    for name, p0, nrm, al, L in walls():
        rays = bad = 0
        samples = []
        k = 0
        while k * 0.5 <= L + 1e-6:
            base = p0 + al * (k * 0.5)
            for d in (0.4, 0.7, 1.0):
                for ez in (1.04, 1.3, 1.58, 1.9, 2.2, 2.5):
                    o = base + nrm * d + Vector((0, 0, ez))
                    for ia in range(13):
                        az = math.radians(-60 + 10 * ia)
                        for ie in range(13):
                            el = math.radians(-30 + 7.5 * ie)
                            h = -nrm * math.cos(az) + al * math.sin(az)
                            dv = (h * math.cos(el) + Vector((0, 0, math.sin(el)))).normalized()
                            rays += 1
                            if leaks(bvh, o, dv):
                                bad += 1
                                if len(samples) < 12:
                                    samples.append({"eye": [round(v, 2) for v in o], "dir": [round(v, 3) for v in dv]})
            k += 1
        res[name] = {"rays": rays, "leaks": bad, "samples": samples}
        print("SIGHT A", name, rays, bad, flush=True)
    return res


def test_b(bvh):
    eyes = {"front": [], "back": [], "west": [], "east": []}
    for x in [13.0 + 1.5 * i for i in range(13)]:
        for y in (12.0, 15.0, 18.0):
            for z in (1.6, 2.3, 3.0):
                eyes["front"].append(Vector((x, y, z)))
        for y in (22.0, 22.6, 23.2):
            eyes["front"].append(Vector((x, y, 5.1)))
        for y in (35.2, 35.8):
            for z in (1.6, 2.3, 3.0):
                eyes["back"].append(Vector((x, y, z)))
    for y in [23.0 + 1.0 * i for i in range(13)]:
        for x in (4.0, 7.0):
            for z in (1.6, 2.3, 3.0):
                eyes["west"].append(Vector((x, y, z)))
                eyes["east"].append(Vector((44.0 - x, y, z)))
        for x in (11.0, 11.8):
            eyes["west"].append(Vector((x, y, 5.1)))
            eyes["east"].append(Vector((44.0 - x, y, 5.1)))
    res = {}
    for name, p0, nrm, al, L in walls():
        centre = p0 + nrm * WALL                                  # the wall centre line (the plate)
        targets = []
        k = 0
        while k * 0.15 <= L + 1e-6:
            for z in (5.63, 5.68, 5.73, 5.78):
                targets.append(centre + al * (k * 0.15) + Vector((0, 0, z)))
            q = centre + al * (k * 0.15)
            if name == "front" and len(VOLS) > 1 and _FR["x_a"] - 0.2 <= q.x <= _FR["x_b"] + 0.2:
                for z in (5.86, 5.92, 5.98):      # round 3: between the raised centre plate and the centre sarking
                    targets.append(q + Vector((0, 0, z)))
            k += 1
        rays = bad = 0
        samples = []
        for o in eyes[name]:
            for tg in targets:
                dv = (tg - o).normalized()
                rays += 1
                if leaks(bvh, o, dv):
                    bad += 1
                    if len(samples) < 12:
                        samples.append({"eye": [round(v, 2) for v in o], "target": [round(v, 3) for v in tg]})
        res[name] = {"eyes": len(eyes[name]), "rays": rays, "leaks": bad, "samples": samples}
        print("SIGHT B", name, rays, bad, flush=True)
    return res


bvh = build_bvh()
A = test_a(bvh)
B = test_b(bvh)
tot_a = sum(v["leaks"] for v in A.values())
tot_b = sum(v["leaks"] for v in B.values())
out = {"interior": "body 0.25 m inside the inner wall faces, +0.55 up to 0.16 m under the upper roof planes (the rafter bays count); round 3: plus the volume under the raised centre plane between the diagonals",
       "A_wall_heads": A, "B_upper_eave": B, "leaks_A": tot_a, "leaks_B": tot_b,
       "rays_A": sum(v["rays"] for v in A.values()), "rays_B": sum(v["rays"] for v in B.values()),
       "passed": tot_a == 0 and tot_b == 0}
OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
print("SIGHT passed", out["passed"], "A", tot_a, "/", out["rays_A"], "B", tot_b, "/", out["rays_B"], flush=True)
