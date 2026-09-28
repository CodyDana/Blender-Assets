"""Snow Flower sheath renders - always from the SHIPPED maps (image textures only), never from the procedural high.

    blender -b --factory-startup --python shv4_render.py -- --set <set> --out <dir>

Sets (each loads the exported FBX files and the exported PNGs, so they show the shipped bytes):
    refview   front orthographic at the reference's own pixel grid (K mm per px, mouth at row 31, axis at x 505.5,
              1024 x 1536) with a sheet-like studio light on white -> ref_front.png (RGBA)
    details   throat / band / chape close-ups framed like the reference crops (orthographic, 3x the reference scale)
    fit       the v4 sword sheathed via the Holster socket (from the sidecar): front, 3/4, and a cutaway (the front half
              of the sheath removed by a plane) showing the blade in its cavity
    gallery   hero 3/4 on a dark studio, back view, side view, wireframe, LOD strip
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "shv4_lib"))   # look-match: frozen sfv4_* helpers
sys.path.insert(0, str(HERE.parents[1]))
import shv4_spec as S  # noqa: E402
import sfv4_look as LK  # noqa: E402
import sfv4_render as R  # noqa: E402

ROOT = S.ROOT
import os as _os0
#: SH4_SHEATH_DIR renders another copy of the sheath (e.g. the pre-look-match backup, for same-light before/after)
EXP = Path(_os0.environ.get("SH4_SHEATH_DIR", str(ROOT / "Exports" / "SnowFlower" / "v4")))
TEX = EXP / "Textures"


def load_sheath(prefix="SH"):
    bpy.ops.import_scene.fbx(filepath=str(EXP / "SM_SnowFlower_Sheath.fbx"))
    st = "T_SnowFlower_Sheath"
    mats = {}
    for slot in (S.SLOT_LACQUER, S.SLOT_SILVER):
        mats[slot] = LK.make_game_material(slot + "_shipped", TEX / f"{st}_BC.png", TEX / f"{st}_ORM.png", TEX / f"{st}_N.png")
    objs = {}
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name.startswith("SM_SnowFlower_Sheath_LOD"):
            for i, sl in enumerate(o.material_slots):
                nm = sl.material.name.split(".")[0] if sl.material else ""
                if nm in mats:
                    o.material_slots[i].material = mats[nm]
            objs[int(o.name.split("_LOD")[1][:1])] = o
        if o.name.startswith("UCX_"):
            o.hide_render = True
    return objs


def load_sword():
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(S.SWORD_FBX))
    new = [o for o in bpy.data.objects if o not in before]
    mats = {}
    import sfv4_spec as SW
    for slot, stem in SW.SLOT_TEX.items():
        STX = S.SWORD_DIR / "Textures"
        mats[slot] = LK.make_game_material(slot + "_shipped", STX / f"{stem}_BC.png", STX / f"{stem}_ORM.png", STX / f"{stem}_N.png")
    objs = {}
    for o in new:
        if o.type == "MESH" and o.name.startswith("SM_SnowFlower_LOD"):
            for i, sl in enumerate(o.material_slots):
                nm = sl.material.name.split(".")[0] if sl.material else ""
                if nm in mats:
                    o.material_slots[i].material = mats[nm]
            objs[int(o.name.split("_LOD")[1][:1])] = o
        if o.name.startswith("UCX_"):
            o.hide_render = True
    root = [o for o in new if o.parent is None]
    return objs, root


def holster_matrix():
    import shv4_verify as V
    side = json.loads((EXP / "SM_SnowFlower_Sheath.sockets.json").read_text(encoding="utf-8"))
    rec = next(r for r in side["sockets"] if r["socket"] == "Holster")
    M = V.ue_socket_to_blender_matrix(rec)
    M.translation = M.translation / 1000.0
    return M


import os as _os
ENV_MID = float(_os.environ.get("SH4_ENV_MID", "0.14"))
ENV_TOP = float(_os.environ.get("SH4_ENV_TOP", "0.7"))
ENV_BOT = float(_os.environ.get("SH4_ENV_BOT", "0.10"))
EXPOSURE = float(_os.environ.get("SH4_EXPOSURE", "-0.35"))   # the sheet-like studio, calibrated on the lacquer / metal tones


def lights_sheet_sheath(zc_m, size=1.0):
    """Look-match round 1: a studio close to the reference sheet - a soft key from the upper left, two tall vertical
    strip boxes front-left / front-right (the reference's bright lines along the facet ridges and the frames), a low
    fill and a rim.  White background (the camera sees it), grey-gradient reflections."""
    import os
    k = float(os.environ.get("SH4_KEY", "220"))
    st = float(os.environ.get("SH4_STRIP", "60"))
    R.area("Key", (-1.2, -1.3, zc_m + 1.0), (0, 0, zc_m), k, 1.2 * size, (1.0, 0.99, 0.97))
    for nm, x, pw in (("StripL", -0.9, st), ("StripR", 0.9, 0.75 * st)):
        l = bpy.data.lights.new(nm, "AREA")
        l.shape = "RECTANGLE"
        l.size, l.size_y = 0.12 * size, 2.4 * size
        l.energy = pw * R.LIGHT_SCALE
        o = bpy.data.objects.new(nm, l)
        bpy.context.scene.collection.objects.link(o)
        o.location = (x, -1.0, zc_m)
        o.rotation_euler = (Vector((0, 0, zc_m)) - Vector(o.location)).to_track_quat("-Z", "Y").to_euler()
    R.area("Fill", (0.8, -1.6, zc_m - 0.4), (0, 0, zc_m), 40, 1.6 * size, (0.92, 0.95, 1.0))
    R.area("Rim", (0.3, 1.6, zc_m + 0.6), (0, 0, zc_m), 120, 1.4 * size)


def show_only(objs, level):
    for lv, o in objs.items():
        o.hide_render = lv != level


def seat_sword(sword_objs, roots, M):
    """Place the sword (its FBX root) so its pivot sits on the Holster socket (sheath at the world origin)."""
    for r in roots:
        r.matrix_world = M @ r.matrix_world


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def refview(out: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = load_sheath()
    show_only(objs, 0)
    R.base_settings(128, transparent=True)
    zc = float(S.zr(767.5))
    R.world_studio(bg=(1, 1, 1), env_top=ENV_TOP, env_mid=ENV_MID, env_bot=ENV_BOT, env_strength=1.0)
    bpy.context.scene.view_settings.exposure = EXPOSURE
    lights_sheet_sheath(zc / 1000.0, size=1.0)
    scale = 1536 * S.K / 1000.0
    cam = R.cam_ortho("front", zc, float(S.xp(511.5)), scale, 1024, 1536)
    render(out / "ref_front.png")
    # the back and the side at the same grid (no reference exists for them; gallery evidence)
    bpy.data.objects.remove(cam)
    cam = R.cam_ortho("back", zc, -float(S.xp(511.5)), scale, 1024, 1536)
    render(out / "ref_back.png")
    bpy.data.objects.remove(cam)
    cam = R.cam_ortho("side", zc, 0.0, scale, 1024, 1536)
    render(out / "ref_side.png")


def details(out: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = load_sheath()
    show_only(objs, 0)
    R.base_settings(160, transparent=True)
    R.world_studio(bg=(1, 1, 1), env_top=ENV_TOP, env_mid=ENV_MID, env_bot=ENV_BOT)
    bpy.context.scene.view_settings.exposure = EXPOSURE
    # crops in reference px: (name, row0, row1, x0, x1)
    for name, r0, r1, x0, x1 in (("throat", 20, 200, 420, 590), ("band", 270, 335, 430, 580),
                                 ("chape", 1240, 1500, 440, 570), ("vine", 440, 780, 440, 575)):
        zc = float(S.zr(0.5 * (r0 + r1)))
        lights_sheet_sheath(zc / 1000.0, size=0.6)
        w_px, h_px = (x1 - x0) * 4, (r1 - r0) * 4
        scale = max(w_px, h_px) / 4 * S.K / 1000.0
        cam = R.cam_ortho("front", zc, float(S.xp(0.5 * (x0 + x1))), scale, w_px, h_px)
        render(out / f"detail_{name}.png")
        bpy.data.objects.remove(cam)
        for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
            bpy.data.objects.remove(o)
    # perspective close-ups of each fitting (3/4 from the front, above)
    R.base_settings(160, transparent=False)
    R.world_studio(bg=(0.16, 0.17, 0.19), env_top=0.9, env_mid=0.22, env_bot=0.03)
    for name, row in (("throat", 95.0), ("band", 302.0), ("chape", 1380.0)):
        z = float(S.zr(row)) / 1000.0
        R.lights_sheet(z, size=0.5)
        cam = R.cam_persp((0.16, -0.22, z - 0.10), (0.0, 0.0, z), lens=85, roll=math.radians(180), w=1400, h=1400)
        render(out / f"persp_{name}.png")
        bpy.data.objects.remove(cam)
        for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
            bpy.data.objects.remove(o)


def cutaway_modifiers(objs, y_cut=0.0):
    """Remove the FRONT half (y < y_cut) of the sheath with a boolean box (render only)."""
    me = bpy.data.meshes.new("CUTBOX")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    box = bpy.data.objects.new("CUTBOX", me)
    bpy.context.scene.collection.objects.link(box)
    box.scale = (0.5, 0.25, 2.2)
    box.location = (0.0, y_cut - 0.125, 0.3)
    box.hide_render = True
    box.display_type = "WIRE"
    for o in objs:
        mod = o.modifiers.new("cut", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = box
        mod.solver = "EXACT"
    return box


def fit(out: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = load_sheath()
    show_only(objs, 0)
    sw, roots = load_sword()
    for lv, o in sw.items():
        o.hide_render = lv != 0
    M = holster_matrix()
    seat_sword(sw, roots, M)
    R.base_settings(128, transparent=True)
    R.world_studio(bg=(1, 1, 1), env_top=0.9, env_mid=0.24, env_bot=0.04)
    zc = -0.08
    R.lights_sheet(zc, size=1.2)
    # front, whole sheathed sword
    cam = R.cam_ortho("front", zc * 1000, 0.0, 1.45, 700, 1500)
    render(out / "fit_front.png")
    bpy.data.objects.remove(cam)
    cam = R.cam_ortho("side", zc * 1000, 0.0, 1.45, 700, 1500)
    render(out / "fit_side.png")
    bpy.data.objects.remove(cam)
    # 3/4 on a dark studio (dimmer environment: the glossy lacquer at grazing angles mirrors it)
    R.base_settings(128, transparent=False)
    R.world_studio(bg=(0.16, 0.17, 0.19), env_top=0.45, env_mid=0.10, env_bot=0.02)
    cam = R.cam_persp((0.95, -1.75, -0.35), (0.0, 0.0, 0.05), lens=50, roll=math.radians(-100), w=2400, h=1350)
    render(out / "fit_hero.png")
    bpy.data.objects.remove(cam)
    # cutaway: the front half of the sheath removed -> the blade in its cavity (sheath LOD0 + sword LOD0)
    box = cutaway_modifiers([objs[0]], y_cut=0.0)
    R.base_settings(160, transparent=True)
    R.world_studio(bg=(1, 1, 1), env_top=0.9, env_mid=0.3, env_bot=0.06)
    for name, zc_mm, sc_m, w, h in (("full", 260.0, 1.10, 700, 1650), ("mouth", -150.0, 0.16, 1000, 1000),
                                    ("tip", 690.0, 0.16, 1000, 1000)):
        cam = R.cam_ortho("front", zc_mm, 0.0, sc_m, w, h)
        cam.data.clip_start = 0.001
        render(out / f"fit_cutaway_{name}.png")
        bpy.data.objects.remove(cam)
    # oblique cutaway close to the mouth
    cam = R.cam_persp((0.10, -0.26, -0.26), (0.0, 0.0, -0.17), lens=70, roll=math.radians(180), w=1400, h=1400)
    render(out / "fit_cutaway_mouth_persp.png")


def _world_bmesh(objs, scale=1000.0):
    import bmesh
    bm = bmesh.new()
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        me = o.evaluated_get(dg).to_mesh()
        me.transform(Matrix.Scale(scale, 4) @ o.matrix_world)
        bm.from_mesh(me)
        o.evaluated_get(dg).to_mesh_clear()
    return bm


def _section_segments(bm_src, z):
    import bmesh
    bm = bm_src.copy()
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                                 plane_co=(0.0, 0.0, z), plane_no=(0.0, 0.0, 1.0))
    segs = [(tuple(e.verts[0].co[:2]), tuple(e.verts[1].co[:2])) for e in res["geom_cut"]
            if isinstance(e, bmesh.types.BMEdge)]
    bm.free()
    return segs


def _seg_dist(p, a, b):
    import numpy as np
    p, a, b = (np.asarray(v, float) for v in (p, a, b))
    ab = b - a
    t = max(0.0, min(1.0, float((p - a) @ ab / max(ab @ ab, 1e-12))))
    return float(np.linalg.norm(p - (a + t * ab)))


def sections(out: Path):
    """X-ray sections: the shipped sheath LOD0 and the shipped sword LOD0 (seated by the Holster socket) cut at seven
    stations; grey = sheath, blue = sword; each label gives the measured minimum blade-to-sheath clearance there."""
    import numpy as np
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = load_sheath()
    sw, roots = load_sword()
    seat_sword(sw, roots, holster_matrix())
    bm_s = _world_bmesh([objs[0]])
    bm_w = _world_bmesh([sw[0]])
    stations = [("mouth + 3 mm", S.Z_MOUTH + 3.0), ("below the throat, row 172", float(S.zr(172))),
                ("mid band, row 304", float(S.zr(304))), ("row 600", float(S.zr(600))), ("row 900", float(S.zr(900))),
                ("row 1250 (tightest wall)", float(S.zr(1250))), ("chape, blade tip - 8 mm", 715.0)]
    mat_s = bpy.data.materials.new("sec_sheath")
    mat_w = bpy.data.materials.new("sec_sword")
    mat_t = bpy.data.materials.new("sec_text")
    for m, c in ((mat_s, (0.12, 0.12, 0.13, 1)), (mat_w, (0.10, 0.35, 0.95, 1)), (mat_t, (0.05, 0.05, 0.05, 1))):
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        o_ = nt.nodes.new("ShaderNodeOutputMaterial")
        e_ = nt.nodes.new("ShaderNodeEmission")
        e_.inputs["Color"].default_value = c
        nt.links.new(e_.outputs[0], o_.inputs[0])
    for o in list(bpy.data.objects):
        o.hide_render = True
    report = []
    cols = 4
    pitch_x, pitch_y = 120.0, 80.0
    for k, (label, z) in enumerate(stations):
        ox, oy = (k % cols) * pitch_x, -(k // cols) * pitch_y
        ss = _section_segments(bm_s, z)
        ws = _section_segments(bm_w, z)
        pts_w = [p for s in ws for p in s]
        dmin = min((_seg_dist(p, a, b) for p in pts_w for a, b in ss), default=float("nan"))
        report.append({"station": label, "z_mm": round(z, 2), "row": round(float(S.row_of(z)), 1),
                       "sheath_segments": len(ss), "blade_segments": len(ws), "min_clearance_mm": round(dmin, 3)})
        for segs, mat, rad in ((ss, mat_s, 0.18), (ws, mat_w, 0.16)):
            if not segs:
                continue
            cu = bpy.data.curves.new(f"sec{k}", "CURVE")
            cu.dimensions = "3D"
            cu.bevel_depth = rad
            for a, b in segs:
                sp = cu.splines.new("POLY")
                sp.points.add(1)
                sp.points[0].co = (a[0] + ox, a[1] + oy, 0.0, 1.0)
                sp.points[1].co = (b[0] + ox, b[1] + oy, 0.0, 1.0)
            ob = bpy.data.objects.new(f"sec{k}", cu)
            ob.data.materials.append(mat)
            bpy.context.scene.collection.objects.link(ob)
        t = bpy.data.curves.new(f"lab{k}", "FONT")
        t.body = f"{label}\nmin clearance {dmin:.2f} mm"
        t.size = 4.2
        to = bpy.data.objects.new(f"lab{k}", t)
        to.location = (ox - 50.0, oy - 30.0, 0.0)
        to.data.materials.append(mat_t)
        bpy.context.scene.collection.objects.link(to)
    t = bpy.data.curves.new("title", "FONT")
    t.body = ("SM_SnowFlower_Sheath LOD0 (grey) with SM_SnowFlower LOD0 (blue) on the Holster socket - sections, "
              "seen from the mouth; front (vine) face down, +X (blade spine) right. Units: the grid pitch is 120 x 80 mm.")
    t.size = 3.2
    to = bpy.data.objects.new("title", t)
    to.location = (-55.0, 36.0, 0.0)
    to.data.materials.append(mat_t)
    bpy.context.scene.collection.objects.link(to)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("white")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    sc.view_settings.view_transform = "Standard"
    cam = bpy.data.objects.new("secam", bpy.data.cameras.new("secam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = cols * pitch_x / 1000.0 * 1000.0
    cam.location = ((cols - 1) * pitch_x / 2, -pitch_y / 2 + 5, 500.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    cam.data.clip_end = 2000.0
    sc.render.resolution_x, sc.render.resolution_y = 2400, 1300
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    render(out / "fit_sections.png")
    (out / "fit_sections.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("SH4_SECTIONS", json.dumps(report), flush=True)


def gallery(out: Path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = load_sheath()
    show_only(objs, 0)
    R.base_settings(128, transparent=False)
    # a dimmer studio than the reference views: the glossy lacquer seen along its length mirrors the environment
    R.world_studio(bg=(0.16, 0.17, 0.19), env_top=0.45, env_mid=0.10, env_bot=0.02)
    R.lights_sheet(0.25, size=1.2)
    cam = R.cam_persp((0.85, -1.55, 0.05), (0.0, 0.0, 0.30), lens=50, roll=math.radians(-95), w=2400, h=1350)
    render(out / "hero.png")
    # wireframe over the hero pose
    o = objs[0]
    wm = o.modifiers.new("wire", "WIREFRAME")
    wm.thickness = 0.00022
    wm.use_replace = False
    wm.material_offset = 2
    mw = bpy.data.materials.new("SH4_Wire")
    mw.use_nodes = True
    bs = next(n for n in mw.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (0.9, 0.55, 0.1, 1)
    bs.inputs["Emission Color"].default_value = (0.9, 0.55, 0.1, 1)
    bs.inputs["Emission Strength"].default_value = 1.5
    o.data.materials.append(mw)
    render(out / "wire.png")
    o.modifiers.remove(o.modifiers["wire"])
    o.data.materials.pop()
    bpy.data.objects.remove(cam)
    # back, 3/4 from behind (the plain back and the belt band)
    cam = R.cam_persp((-0.85, 1.55, 0.05), (0.0, 0.0, 0.30), lens=50, roll=math.radians(95), w=2400, h=1350)
    render(out / "back_hero.png")
    bpy.data.objects.remove(cam)
    # LOD strip, front view
    saved = {lv: ob.matrix_world.copy() for lv, ob in objs.items()}
    for lv, ob in objs.items():
        ob.hide_render = False
        ob.matrix_world = Matrix.Translation((-(lv - 1) * 0.16, 0, 0)) @ saved[lv]
    cam = R.cam_ortho("front", 315.0, 0.0, 1.10, 1100, 1650)
    render(out / "lod_strip.png")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    if not out.is_absolute():
        raise SystemExit("--out must be absolute")
    out.mkdir(parents=True, exist_ok=True)
    {"refview": refview, "details": details, "fit": fit, "gallery": gallery, "sections": sections}[a.set](out)
    print("SH4_RENDER_DONE", a.set, flush=True)


if __name__ == "__main__":
    main()
