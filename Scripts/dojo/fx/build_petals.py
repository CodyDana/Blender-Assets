"""Build the Yoshino petal meshes and fallen-petal drift clusters, QA and export them (headless Blender 5.2).

    blender -b --factory-startup --python Scripts/dojo/fx/build_petals.py

Petals SM_DKF_Petal_A..F follow the sheet's six petals (A/B/D/F flat and cupped, C curled, E folded) and
SM_DKF_PetalOld_A the browned old petal. Each is a hull of the traced outline (rows x columns, a few dozen
triangles), UV0 = the flat pattern in the petal texture frame, UV1 = the same (inside 0-1, no overlap). Shapes are
made by developable bends (cup, base/tip bend, twist, cylinder rolls) of the flat pattern, so the texture never
stretches. Origin at the area centroid (Niagara mesh particles spin about it), front face = +Z before bending,
length along +Y (base at -Y). Real size: 12.5-14.5 mm.

Drift clusters SM_DKF_PetalDrift_A..C: copies of the petals lying on the ground (origin on the ground at the
cluster centre, lowest point 0.3 mm above it), ~1 in 8 old petals. Their UV0 is shared by design (every petal
samples the same texture; TREE_BUILDING_STUDY 4.12 / P38): the full QA runs per petal unit.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import fx_bl as B  # noqa: E402
import fx_common as fx  # noqa: E402
from make_petal_textures import half_width_at, load_outline, top_at  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402

ROWS = [0.0, 0.08, 0.22, 0.40, 0.58, 0.76, 0.90, 1.0]
MARGIN = 0.012

# name: (length mm, columns, deformation params)
PETALS = {
    "A": (14.0, 4, dict(cup=0.28, base=0.30, tip=-0.05)),
    "B": (13.0, 4, dict(cup=0.42, base=0.14, tip=-0.02)),
    "C": (13.5, 6, dict(cup=0.45, base=0.10, tip=0.0, twist=0.25, rot_y=-0.85,
                        rolls=[dict(p=(0.0, 0.30), d=(1.0, 0.0), side=-1, R=0.42, k=0.40, up=1)])),
    "D": (14.5, 4, dict(cup=0.30, base=0.36, tip=-0.07)),
    "E": (12.5, 6, dict(cup=0.04, base=0.10, tip=0.0,
                        rolls=[dict(p=(-0.03, 0.0), d=(-0.22, 1.0), side=-1, R=0.12, k=0.70, up=1),
                               dict(p=(0.03, 0.0), d=(0.22, 1.0), side=1, R=0.12, k=0.62, up=1)])),
    "F": (13.0, 4, dict(cup=0.34, base=0.30, tip=-0.04, twist=0.15)),
}
OLD = ("OldA", 12.5, 6, dict(cup=0.18, base=0.12, tip=0.05, crumple=0.035,
                             rolls=[dict(p=(0.24, 0.0), d=(0.0, 1.0), side=1, R=0.05, k=0.22, up=1),
                                    dict(p=(-0.25, 0.0), d=(0.0, 1.0), side=-1, R=0.06, k=0.16, up=1)]))


def hull_rows(outline):
    """Row half-widths so the piecewise-linear hull encloses the traced outline by >= MARGIN."""
    ys = np.array(ROWS)
    ys_ext = ys.copy()
    ys_ext[0] = -MARGIN
    ys_ext[-1] = 1.0 + MARGIN
    w = np.array([half_width_at(min(max(y, 0), 1), outline) for y in ys]) + MARGIN
    w[0] = max(w[0], 0.03)
    w[-1] = max(float(np.max(np.abs(np.linspace(-0.35, 0.35, 400))[
        np.array([top_at(x, outline) for x in np.linspace(-0.35, 0.35, 400)]) > 0.9])) + MARGIN, 0.08)
    fine = np.linspace(0, 1, 800)
    need = np.array([half_width_at(y, outline) for y in fine]) + MARGIN
    for _ in range(200):
        hull = np.interp(fine, ys_ext, w)
        short = need - hull
        if short.max() <= 1e-5:
            break
        i = int(np.argmax(short))
        j = int(np.searchsorted(ys_ext, fine[i])) - 1
        j = min(max(j, 0), len(w) - 2)
        w[j] += short[i] * 0.6
        w[j + 1] += short[i] * 0.6
    return ys_ext, w


def roll(P, p, d, side, R, k, up):
    """Wrap the part of the sheet on `side` of the in-plane line (p, d) onto a cylinder of radius R (k*pi max)."""
    d = np.array(d, float) / np.linalg.norm(d)
    n = np.array([d[1], -d[0]]) * side  # in-plane normal toward the rolled side
    out = P.copy()
    rel = P[:, :2] - np.array(p)
    s = rel @ n
    amax = k * math.pi
    for i in np.nonzero(s > 0)[0]:
        si = s[i]
        base = P[i].copy()
        base[:2] -= si * n
        a = min(si / R, amax)
        extra = max(0.0, si - amax * R)
        nn = np.array([n[0], n[1], 0.0])
        zz = np.array([0, 0, float(up)])
        pos = base + nn * (R * math.sin(a)) + zz * (R * (1 - math.cos(a)))
        pos += extra * (nn * math.cos(a) + zz * math.sin(a))
        out[i] = pos
    return out


def petal_mesh(name, length_mm, cols, prm, outline, seed=0):
    ys, w = hull_rows(outline)
    verts, uvs = [], []
    for y, hw in zip(ys, w):
        for c in range(cols + 1):
            x = -hw + 2 * hw * c / cols
            verts.append((x, y, 0.0))
            uvs.append(fx.petal_to_uv(x, y))
    P = np.array(verts, float)
    x, y = P[:, 0], P[:, 1]
    z = prm.get("cup", 0) * x * x / 0.35
    z += prm.get("base", 0) * np.clip(1 - y / 0.30, 0, None) ** 2
    z += prm.get("tip", 0) * np.clip((y - 0.55) / 0.45, 0, None) ** 2
    if prm.get("crumple"):
        rng = np.random.default_rng(seed + 5)
        z += prm["crumple"] * np.sin(9 * x + rng.uniform(0, 6)) * np.sin(7 * y + rng.uniform(0, 6))
        z += rng.normal(0, prm["crumple"] * 0.35, len(z))
    P[:, 2] = z
    for r in prm.get("rolls", []):
        P = roll(P, **r)
    tw = prm.get("twist", 0.0)
    if tw:
        a = tw * (P[:, 1] - 0.3)
        xn = P[:, 0] * np.cos(a) - P[:, 2] * np.sin(a)
        zn = P[:, 0] * np.sin(a) + P[:, 2] * np.cos(a)
        P[:, 0], P[:, 2] = xn, zn
    ry = prm.get("rot_y", 0.0)
    if ry:  # rest pose on its side: the lengthwise curl then reads as the sheet's crescent from above
        xn = P[:, 0] * math.cos(ry) + P[:, 2] * math.sin(ry)
        zn = -P[:, 0] * math.sin(ry) + P[:, 2] * math.cos(ry)
        P[:, 0], P[:, 2] = xn, zn
    P *= length_mm / 1000.0
    me = bpy.data.meshes.new(name)
    faces = []
    for r in range(len(ys) - 1):
        for c in range(cols):
            a = r * (cols + 1) + c
            faces.append((a, a + 1, a + cols + 2, a + cols + 1))
    me.from_pydata([tuple(v) for v in P], [], faces)
    me.update()
    uv0 = me.uv_layers.new(name="UVMap")
    uv1 = me.uv_layers.new(name="Lightmap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uv0.data[li].uv = (float(uvs[vi][0]), float(uvs[vi][1]))
            uv1.data[li].uv = (float(uvs[vi][0]), float(uvs[vi][1]))
    for poly in me.polygons:
        poly.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    # origin at the area centroid
    bm = bmesh.new()
    bm.from_mesh(me)
    tot, acc = 0.0, Vector()
    for f in bm.faces:
        a = f.calc_area()
        tot += a
        acc += f.calc_center_median() * a
    bm.free()
    c = acc / tot
    me.transform(__import__("mathutils").Matrix.Translation(-c))
    return ob


def main():
    assert_owner(fx.LOCK_ASSET, "claude")
    B.reset_scene()
    sc = bpy.context.scene
    outline = load_outline()
    m_petal = B.petal_material("MI_DKF_Petal", "Petal")
    m_old = B.petal_material("MI_DKF_PetalOld", "PetalOld", has_back=False, translucency=0.35)
    col_p = bpy.data.collections.new("Petals")
    sc.collection.children.link(col_p)
    petals = {}
    for i, (key, (L, cols, prm)) in enumerate(PETALS.items()):
        ob = petal_mesh(f"SM_DKF_Petal_{key}", L, cols, prm, outline, seed=i)
        ob.data.materials.append(m_petal)
        petals[key] = ob
    key, L, cols, prm = OLD
    old = petal_mesh("SM_DKF_PetalOld_A", L, cols, prm, outline, seed=9)
    old.data.materials.append(m_old)
    petals["OldA"] = old
    for i, ob in enumerate(petals.values()):
        sc.collection.objects.unlink(ob)
        col_p.objects.link(ob)
        ob.location = (0.03 * i, 0, 0)  # display only; reset to 0 before QA/export

    # --- drift clusters (fallen petals): petal copies resting on the ground
    col_d = bpy.data.collections.new("Drifts")
    sc.collection.children.link(col_d)
    drifts = {}
    rng = np.random.default_rng(42)
    specs = {"A": (0.18, 26), "B": (0.28, 48), "C": (0.40, 90)}  # radius m, petal count
    keys = list(PETALS)
    for dname, (rad, count) in specs.items():
        bm = bmesh.new()
        uv_l = bm.loops.layers.uv.new("UVMap")
        uv_l1 = bm.loops.layers.uv.new("Lightmap")
        mat_index = []
        n_old = max(1, round(count / 8))
        old_ids = set(rng.choice(count, n_old, replace=False).tolist())
        placed = []
        for k in range(count):
            src = petals["OldA"] if k in old_ids else petals[keys[rng.integers(0, len(keys))]]
            if src.name.endswith(("_C", "_E")) and rng.random() < 0.6:
                src = petals[keys[rng.choice([0, 1, 3, 5])]]
            me = src.data
            # clumped distribution: 2-4 sub-clumps + scattered strays (the sheet's drifts gather in joints)
            if k % 5 == 0:
                r = rad * math.sqrt(rng.random())
                th = rng.uniform(0, 2 * math.pi)
            else:
                cth = (k % 3) * 2.1 + list(specs).index(dname) * 1.3
                cx, cy = 0.45 * rad * math.cos(cth), 0.45 * rad * math.sin(cth)
                r = rad * 0.35 * math.sqrt(rng.random())
                th = rng.uniform(0, 2 * math.pi)
                r_x, r_y = cx + r * math.cos(th), cy + r * math.sin(th)
                r, th = math.hypot(r_x, r_y), math.atan2(r_y, r_x)
            pos = Vector((r * math.cos(th), r * math.sin(th), 0))
            yaw = rng.uniform(0, 2 * math.pi)
            flip = rng.random() < 0.3  # some lie back-up
            tilt = rng.normal(0, 0.12)
            from mathutils import Euler, Matrix
            rot = Euler((math.pi if flip else 0.0, tilt, yaw), "XYZ").to_matrix().to_4x4()
            verts = [rot @ v.co for v in me.vertices]
            zmin = min(v.z for v in verts)
            # stack on earlier petals nearby (overlap)
            lift = 0.0
            for (pp, rr) in placed:
                if (pp - pos).length < rr:
                    lift = max(lift, 0.0006)
            off = pos + Vector((0, 0, -zmin + 0.0003 + lift))
            placed.append((pos, 0.006))
            bv = [bm.verts.new(v + off) for v in verts]
            for poly in me.polygons:
                f = bm.faces.new([bv[i] for i in poly.vertices])
                f.smooth = True
                f.material_index = 1 if src is petals["OldA"] else 0
                for loop, li in zip(f.loops, poly.loop_indices):
                    loop[uv_l].uv = me.uv_layers[0].data[li].uv
                    loop[uv_l1].uv = me.uv_layers[0].data[li].uv
        me_d = bpy.data.meshes.new(f"SM_DKF_PetalDrift_{dname}")
        bm.to_mesh(me_d)
        bm.free()
        # lightmap UV: pack the copies into 0-1 without overlap
        ob = bpy.data.objects.new(me_d.name, me_d)
        col_d.objects.link(ob)
        me_d.materials.append(m_petal)
        me_d.materials.append(m_old)
        drifts[dname] = ob
        bpy.context.view_layer.objects.active = ob
        for o in bpy.context.view_layer.objects:
            o.select_set(o == ob)
        me_d.uv_layers.active_index = 1
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        me_d.uv_layers.active_index = 0
        ob.location = (0.0, 0.5 + 0.9 * list(specs).index(dname), 0)

    # --- QA + export
    report = {"petals": {}, "drifts": {}, "exports": {}}
    for ob in list(petals.values()) + list(drifts.values()):
        saved = ob.location.copy()
        ob.location = (0, 0, 0)
        bpy.context.view_layer.update()
        is_drift = "Drift" in ob.name
        r = qa_check([ob], require_uv1=True, require_ucx=False, budget_tris=None if is_drift else 120,
                     uv0_tile_range=(0.0, 1.0))
        fails = [c for c in r["checks"] if not c["passed"]]
        entry = {"passed": r["passed"], "triangles": r["triangles"].get(ob.name), "fails": fails}
        if is_drift:
            # UV0 overlap is by design (shared petal texture); everything else must pass
            other = [c for c in fails if c["name"] != "uv_no_overlap"]
            entry["passed_except_shared_uv0"] = not other
        (report["drifts"] if is_drift else report["petals"])[ob.name] = entry
        out = fx.EXPORT / f"{ob.name}.fbx"
        res = export_fbx(str(out), [ob], kind="static")
        report["exports"][ob.name] = {"file": str(out.relative_to(fx.ROOT)), "warnings": res.get("warnings")}
        ob.location = saved
    dims = {}
    for k, ob in petals.items():
        bb = [ob.matrix_world.inverted() @ (ob.matrix_world @ Vector(c)) for c in ob.bound_box]
        xs = [v.x for v in bb]; ys = [v.y for v in bb]; zs = [v.z for v in bb]
        dims[ob.name] = [round((max(a) - min(a)) * 1000, 2) for a in (xs, ys, zs)]
    report["dims_mm_xyz"] = dims
    fx.write_json(fx.WORK / "json/petals_qa.json", report)
    fx.BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(fx.BLEND))
    for n, e in {**report["petals"], **report["drifts"]}.items():
        print("QA", n, e["passed"], e.get("passed_except_shared_uv0", ""), e["triangles"],
              [f["name"] for f in e["fails"]])
    print("DIMS", json.dumps(dims))


if __name__ == "__main__":
    main()
