"""Development aid: list the non-manifold edges (boundary / multi-face) and the UD offenders of objects in a blend, in
frame M (mm). Inside Blender:  blender -b <blend> --factory-startup --python smg_nm_probe.py -- name [name...]"""
from __future__ import annotations

import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smg_common import GRIP  # noqa: E402

names = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for nm in names or [o.name for o in bpy.data.objects if o.type == "MESH"]:
    o = bpy.data.objects.get(nm)
    if o is None:
        print("NO", nm)
        continue
    bm = bmesh.new()
    bm.from_mesh(o.data)
    pts = []
    for e in bm.edges:
        n = len(e.link_faces)
        if n != 2:
            m = (e.verts[0].co + e.verts[1].co) / 2 * 1000.0
            pts.append((n, round(m.x + GRIP[0], 2), round(m.y + GRIP[1], 2), round(m.z + GRIP[2], 2),
                        round(e.calc_length() * 1000, 3)))
    print("OBJ", nm, "non-manifold edges", len(pts))
    for p in pts[:60]:
        print("  faces=%d  M (%.2f, %.2f, %.2f) len %.3f" % p)
    try:
        from gunlib import ud
        r = ud.check_object(o)
        print("  UD", {k: r.get(k) for k in ("unreal_drops", "min_area_mm2", "edges_under_0.05mm", "needles_under_0.02mm",
                                              "strip_polygons_under_0.1mm", "pass_ud1", "pass_ud2")})
        loc = ud.locate(o, 12)
        for k, v in loc.items():
            print("   ", k, str(v)[:600])
    except Exception as ex:  # noqa: BLE001
        print("  UD error", ex)
    bm.free()


def groups_probe(o):
    """Locate the zero-tangent-risk groups (needle corners / edge-on), M frame."""
    me = o.data
    nl = len(me.loops)
    fn = np.array([p.normal[:] for p in me.polygons])
    LV = np.array([l.vertex_index for l in me.loops])
    V = np.array([v.co[:] for v in me.vertices]) * 1000.0 + np.asarray(GRIP)
    CN = np.array([c.vector[:] for c in me.corner_normals], float)
    face = np.zeros(nl, int)
    nxt = np.zeros(nl, int)
    prv = np.zeros(nl, int)
    for p in me.polygons:
        idx = np.arange(p.loop_start, p.loop_start + p.loop_total)
        face[idx] = p.index
        nxt[idx] = np.roll(idx, -1)
        prv[idx] = np.roll(idx, 1)
    e1 = V[LV[nxt]] - V[LV]
    e2 = V[LV[prv]] - V[LV]
    ang = np.degrees(np.arctan2(np.linalg.norm(np.cross(e1, e2), axis=1), (e1 * e2).sum(1)))
    dot = np.abs((fn[face] * CN).sum(1))
    key = np.c_[LV, np.round(CN * 1e4)]
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    ga = np.zeros(inv.max() + 1)
    np.maximum.at(ga, inv, ang)
    gd = np.zeros(inv.max() + 1)
    np.maximum.at(gd, inv, dot)
    for g in np.nonzero(ga < 0.5)[0][:10]:
        li = np.nonzero(inv == g)[0]
        print("   needle group at", np.round(V[LV[li[0]]], 2), "corners", np.round(ang[li], 3), "faces", len(li))
    for g in np.nonzero(gd < 0.1)[0][:10]:
        li = np.nonzero(inv == g)[0]
        print("   edge-on group at", np.round(V[LV[li[0]]], 2), "dots", np.round(dot[li], 3), "corners",
              np.round(ang[li], 2))


for nm in names:
    o = bpy.data.objects.get(nm)
    if o is not None:
        print("GROUPS", nm)
        groups_probe(o)
