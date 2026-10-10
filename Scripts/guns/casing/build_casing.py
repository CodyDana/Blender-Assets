"""Build + export SM_Casing_762x39 (shooting prototype step G1, plan 4.2). Headless Blender 5.2:

    blender.exe -b --factory-startup --python Scripts/guns/casing/build_casing.py

The spent 7.62x39 steel case as a solid of revolution of the C.I.P. profile (casing_spec), LOD0 24 segments,
LOD1 8, LOD2 6; UV0 = the revolve layout; analytic custom normals (hard at the profile corners, soft shoulder);
textures painted per ring (casing_textures). Gates before export: qa_check (Scripts/pipeline), the dimension gate
(casing_measure, 0.05 mm), the tri budget, UD1/UD2 (gunlib.ud, no triangle under 0.005 mm^2 / the 0.01 mm^2 margin)
and the MikkTSpace collapse diagnostics (gunlib.tspace). Exported only through Scripts/pipeline.export_fbx.

Writes: Exports/Guns/Casing/SM_Casing_762x39.fbx + .sockets.json + Textures/T_Casing_762x39_{BC,ORM,N}.png,
Assets/Guns/Casing_762x39.blend, WorkFiles/guns/casing/casing_build.json (+ showcase_pair.blend, not in git).
Lock: Casing762 (Scripts/pipeline/lock.py).
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(HERE), str(ROOT / "Scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import casing_spec as CS  # noqa: E402
from casing_measure import measure  # noqa: E402
from casing_textures import paint  # noqa: E402
from pipeline import lock  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.helpers import make_lod_group, make_socket  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.textures import load_data_image, write_png  # noqa: E402

NAME = "SM_Casing_762x39"
MAT = "M_Casing_762x39"
TEX_KEY = "T_Casing_762x39"
EXP = ROOT / "Exports" / "Guns" / "Casing"
TEXD = EXP / "Textures"
ASSET = ROOT / "Assets" / "Guns" / "Casing_762x39.blend"
WORK = ROOT / "WorkFiles" / "guns" / "casing"
# Unreal screen sizes: the case's bounds sphere (r ~ 2 cm) is ~0.09 of the screen at 0.4 m (ADS, FOV 55) and ~0.04
# at 1 m: LOD0 inside ~0.8 m, LOD1 to ~2.5 m, LOD2 beyond (the house default 1.0 / 0.5 / 0.25 would park a casing on
# its 6-sided LOD2 everywhere but a few centimetres from the lens).
SCREEN_SIZES = [1.0, 0.05, 0.015]


def log(*a):
    print("[casing]", *a, flush=True)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------- geometry
def band_normal(a, b):
    """Outward normal of the profile segment a -> b in the (r, z) plane (the profile walks around the solid)."""
    dr, dz = b["r"] - a["r"], b["z"] - a["z"]
    L = math.hypot(dr, dz)
    return (dz / L, -dr / L)          # (n_r, n_z)


def revolve(name, prof, N, com_z, vmap):
    """Mesh object: the profile revolved N times about the axis (Blender +X = case axis, x = z - com_z)."""
    mm = 0.001
    bm = bmesh.new()
    lay_p = bm.verts.layers.int.new("pidx")
    lay_c = bm.verts.layers.int.new("col")
    rings = []
    for i, p in enumerate(prof):
        x = (p["z"] - com_z) * mm
        if p["r"] == 0.0:
            v = bm.verts.new((x, 0.0, 0.0))
            v[lay_p], v[lay_c] = i, -1
            rings.append([v])
        else:
            ring = []
            for k in range(N):
                th = 2.0 * math.pi * k / N
                v = bm.verts.new((x, p["r"] * math.cos(th) * mm, p["r"] * math.sin(th) * mm))
                v[lay_p], v[lay_c] = i, k
                ring.append(v)
            rings.append(ring)
    flay_b = bm.faces.layers.int.new("band")
    flay_k = bm.faces.layers.int.new("fcol")
    for i in range(len(prof) - 1):
        A, B = rings[i], rings[i + 1]
        for k in range(N):
            k1 = (k + 1) % N
            if len(A) == 1:
                vs = (A[0], B[k1], B[k])
            elif len(B) == 1:
                vs = (A[k], A[k1], B[0])
            else:
                vs = (A[k], A[k1], B[k1], B[k])
            f = bm.faces.new(vs)
            f[flay_b], f[flay_k] = i, k
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="FIXED", ngon_method="BEAUTY")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)

    # UV0 + custom normals, per loop
    nseg = [band_normal(prof[i], prof[i + 1]) for i in range(len(prof) - 1)]
    pidx = np.zeros(len(me.vertices), int)
    me.attributes["pidx"].data.foreach_get("value", pidx)
    colv = np.zeros(len(me.vertices), int)
    me.attributes["col"].data.foreach_get("value", colv)
    band = np.zeros(len(me.polygons), int)
    me.attributes["band"].data.foreach_get("value", band)
    fcol = np.zeros(len(me.polygons), int)
    me.attributes["fcol"].data.foreach_get("value", fcol)
    uvl = me.uv_layers.new(name="UVMap")
    uv = np.zeros((len(me.loops), 2))
    nl = np.zeros((len(me.loops), 3))
    for poly in me.polygons:
        b, kf = int(band[poly.index]), int(fcol[poly.index])
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            i, kv = int(pidx[vi]), int(colv[vi])
            if kv < 0:
                u = (kf + 0.5) / N
                th = 2.0 * math.pi * u
            else:
                kk = kf if kv == kf else kf + 1          # kf + 1 may be N: the seam column gets u = 1
                u = kk / N
                th = 2.0 * math.pi * kv / N
            uv[li] = (u, vmap(i, prof[i]))
            mode = prof[i]["mode"][1] if i == b else prof[i]["mode"][0]
            if mode == "avg" and 0 < i < len(prof) - 1:
                n_r = nseg[i - 1][0] + nseg[i][0]
                n_z = nseg[i - 1][1] + nseg[i][1]
            elif mode == "avg":                           # a pole: straight along the axis
                n_r, n_z = 0.0, math.copysign(1.0, nseg[b][1])
            else:
                n_r, n_z = nseg[b]
            L = math.hypot(n_r, n_z)
            nl[li] = (n_z / L, n_r / L * math.cos(th), n_r / L * math.sin(th))
    uvl.data.foreach_set("uv", uv.ravel())
    for a in ("pidx", "col", "band", "fcol"):
        me.attributes.remove(me.attributes[a])
    me.shade_smooth()
    me.normals_split_custom_set([tuple(x) for x in nl])
    return ob


def signed_volume_mm3(ob):
    me = ob.data
    me.calc_loop_triangles()
    V = np.array([v.co[:] for v in me.vertices]) * 1000.0
    T = np.array([t.vertices[:] for t in me.loop_triangles])
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


# ---------------------------------------------------------------------------------------------- material
def build_material(paths):
    m = bpy.data.materials.new(MAT)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bc = nt.nodes.new("ShaderNodeTexImage")
    bc.image = bpy.data.images.load(str(paths["BC"]), check_existing=True)
    bc.image.colorspace_settings.name = "sRGB"
    orm = nt.nodes.new("ShaderNodeTexImage")
    orm.image = load_data_image(paths["ORM"])
    nrm = nt.nodes.new("ShaderNodeTexImage")
    nrm.image = load_data_image(paths["N"])
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    # DirectX normal (house rule) -> Blender (OpenGL): flip green
    sepn = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(nrm.outputs["Color"], sepn.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sepn.outputs["Green"], inv.inputs[1])
    comb = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sepn.outputs["Red"], comb.inputs["Red"])
    nt.links.new(inv.outputs["Value"], comb.inputs["Green"])
    nt.links.new(sepn.outputs["Blue"], comb.inputs["Blue"])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(comb.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    m.diffuse_color = (0.14, 0.12, 0.05, 1.0)
    return m


# ---------------------------------------------------------------------------------------------- main
def main():
    t0 = time.time()
    lock.assert_owner("Casing762", "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    rep = {"asset": NAME, "built": time.strftime("%Y-%m-%dT%H:%M:%S"), "cip": CS.CIP, "extra": CS.EXTRA}
    mp = CS.mass_properties()
    com = mp["com_z_mm"]
    rep["mass_properties"] = {k: round(v, 4) for k, v in mp.items()}
    rep["mass_properties"]["note"] = ("real hollow steel case (casing_spec.real_inner_r + Berdan pocket); the origin is "
                                      "this centre of mass; the mesh bore is a dark cone, so the mesh volume differs")
    log("mass", rep["mass_properties"])

    # textures
    bc, orm, nrm, tinfo = paint()
    TEXD.mkdir(parents=True, exist_ok=True)
    paths = {"BC": TEXD / f"{TEX_KEY}_BC.png", "ORM": TEXD / f"{TEX_KEY}_ORM.png", "N": TEXD / f"{TEX_KEY}_N.png"}
    write_png(bc, paths["BC"])
    write_png(orm, paths["ORM"])
    write_png(nrm, paths["N"])
    rep["textures"] = {k: {"file": str(p.relative_to(ROOT)).replace("\\", "/"), "size": [512, 512]}
                       for k, p in paths.items()}
    rep["texture_paint"] = tinfo
    mat = build_material(paths)

    # meshes
    vs0 = CS.lod0_v()
    lods = []
    for tag, fn, N in CS.LODS:
        prof = fn()
        if tag == "LOD0":
            vmap = (lambda i, p: vs0[i])
        else:
            vmap = (lambda i, p: CS.v_of_point(p["r"], p["z"], p["tag"]))
        ob = revolve(f"{NAME}_{tag}", prof, N, com, vmap)
        ob.data.materials.append(mat)
        vol = signed_volume_mm3(ob)
        if vol < 0:
            raise SystemExit(f"{ob.name}: normals point inward (volume {vol})")
        lods.append(ob)
        log(tag, len(ob.data.polygons), "tris, mesh volume", round(vol, 2), "mm3")

    # sockets on LOD0 (X along the case axis toward the mouth; Unreal identity rotation)
    lod0 = lods[0]
    make_socket(lod0, "Base", (-com * 0.001, 0.0, 0.0), (0.0, 0.0, 0.0))
    make_socket(lod0, "Mouth", ((CS.CIP["L3"] - com) * 0.001, 0.0, 0.0), (0.0, 0.0, 0.0))
    grp = make_lod_group(NAME, lods)
    grp["lod_screen_sizes"] = json.dumps(SCREEN_SIZES)

    # ------------------------------------------------------------------ gates
    gates = {}
    tris = {o.name.rsplit("_", 1)[1]: len(o.data.polygons) for o in lods}
    gates["tri_budget"] = {"triangles": tris, "budget": CS.TRI_BUDGET, "plan_estimate": {"LOD0": 400, "LOD1": 120,
                           "LOD2": 40}, "pass": all(tris[k] <= CS.TRI_BUDGET[k] for k in tris)}
    q = qa_check(lods, budget_tris=None, texel_density=None, require_ucx=False)
    failed = [c for c in q["checks"] if not c["passed"]]
    gates["qa_check"] = {"passed": q["passed"], "triangles": q["triangles"], "checks": len(q["checks"]),
                         "failed": failed, "require_ucx": False,
                         "boundary_or_info": [c for c in q["checks"] if "boundary" in c["name"]]}
    log("qa_check", q["passed"], [c["name"] for c in failed])
    V0 = np.array([v.co[:] for v in lod0.data.vertices]) * 1000.0
    gates["dimensions"] = measure(V0, 24)
    log("dimensions", gates["dimensions"]["pass"],
        [(r["dim"], r.get("err_mm", r.get("err_deg"))) for r in gates["dimensions"]["rows"]])
    from guns.gunlib import ud, tspace
    udr = [ud.check_object(o) for o in lods]
    gates["ud"] = {"reports": udr, "pass_ud1": all(r["pass_ud1"] for r in udr),
                   "pass_ud2": all(r["pass_ud2"] and r.get("strip_polygons_under_0.1mm", 0) == 0 for r in udr)}
    diag = {}
    for o in lods:
        d = {}
        for fn in ("collapsed", "float32_zero_corners", "edge_on_corners"):
            try:
                res = getattr(tspace, fn)(o.data)
                d[fn] = int(len(res))
            except Exception as exc:  # noqa: BLE001 - diagnostics only
                d[fn] = f"error: {type(exc).__name__}: {exc}"
        diag[o.name] = d
    gates["tangent_diagnostics"] = diag
    log("ud", gates["ud"]["pass_ud1"], gates["ud"]["pass_ud2"], diag)
    rep["gates"] = gates
    ok = all([gates["tri_budget"]["pass"], q["passed"], gates["dimensions"]["pass"], gates["ud"]["pass_ud1"],
              gates["ud"]["pass_ud2"]])
    WORK.mkdir(parents=True, exist_ok=True)
    if not ok:
        (WORK / "casing_build.json").write_text(json.dumps(rep, indent=1, default=str))
        raise SystemExit("[casing] a gate failed: not exported (see casing_build.json)")

    # ------------------------------------------------------------------ export
    res = export_fbx(str(EXP / f"{NAME}.fbx"), [grp], kind="static", lod_screen_sizes=SCREEN_SIZES)
    rep["export"] = {"fbx": res["filepath"], "sidecar": res["sidecar"], "warnings": res["warnings"],
                     "lod_screen_sizes": res["lod_screen_sizes"], "objects": res["objects"], "sockets": res["sockets"]}
    files = [EXP / f"{NAME}.fbx", Path(res["sidecar"])] + list(paths.values())
    rep["sha256"] = {str(p.relative_to(ROOT)).replace("\\", "/"): sha256(p) for p in files}
    log("exported", res["filepath"], res["warnings"])

    # ------------------------------------------------------------------ source .blend + showcase pair (scratch)
    ASSET.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ASSET), relative_remap=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile()
    rep["blend"] = str(ASSET.relative_to(ROOT)).replace("\\", "/")
    coll = bpy.data.collections.new("ShowcasePair")
    sc.collection.children.link(coll)
    a = bpy.data.objects.new("Pair_A", lod0.data)
    b = bpy.data.objects.new("Pair_B", lod0.data)
    for o in (a, b):
        coll.objects.link(o)
    a.location = (0.0, 0.0, 0.0)
    hero = Vector((0.78, -1.0, 0.0)).normalized()
    yaw = math.atan2(-hero.y, -hero.x)                          # case axis away from the hero camera: base faces it
    b.rotation_euler = (0.0, 0.0, yaw)
    b.location = (0.006, 0.028, 0.0)
    for o in (grp,) + tuple(grp.children_recursive):
        o.hide_render = True
    pair = WORK / "showcase_pair.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(pair), copy=True, relative_remap=True)
    rep["showcase_pair_blend"] = str(pair.relative_to(ROOT)).replace("\\", "/")
    rep["seconds"] = round(time.time() - t0, 1)
    (WORK / "casing_build.json").write_text(json.dumps(rep, indent=1, default=str))
    log("DONE", rep["seconds"], "s")


main()
