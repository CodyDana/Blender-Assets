"""Render the STUDY-ONLY reference LP through the pack's own gallery rig (shuriken_lib.render).

Why: the first comparison sheet's "REFERENCE (our rig)" column came from a scratch rig (AgX,
flat world, ad-hoc lights, 85 mm lens), so its numbers (hero 0.30 / top 0.28) were not comparable
with the pack's gallery.  This script uses render.setup_render / build_preview_rig / image_stats
unchanged - same world, lamps, wall card, top band, cameras, view transform and mask pass - so
the reference and the forms are measured apples-to-apples.

Two runs: ``scaled100`` (the 197 mm mesh scaled to 100 mm tip-to-tip, the pack's size class, so
the top view shares the pack's px/mm) and ``native197`` (TOP_FRAME_HEIGHT patched to fit it).

Outputs (WorkFiles only; nothing from the reference is copied into the pack, the maps are read
from References/ and the renders are study material):
    ref_rig_<tag>_persp.png / _top.png (+ the mask passes) and ref_rig_stats.json here.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python ref_on_rig.py -- [--samples 220]
"""
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path.insert(0, str(PROJECT / "Scripts" / "shuriken"))
from shuriken_lib import render as R  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 220
REF = PROJECT / "References" / "Shuriken" / "style_reference"
RES_X, RES_Y = 1600, 900


def world_verts(o):
    me = o.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(o.matrix_world)
    return (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3]


def textured_material(o):
    """The reference's own four maps on a Principled BSDF (read from References/, never copied)."""
    mat = bpy.data.materials.new("M_StyleRef")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def tex(name, cs):
        img = bpy.data.images.load(str(REF / f"shuriken_Shuriken_{name}.png"))
        img.colorspace_settings.name = cs
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = img
        return n

    bc = tex("BaseColor", "sRGB")
    me = tex("Metallic", "Non-Color")
    ro = tex("Roughness", "Non-Color")
    no = tex("Normal", "Non-Color")
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(me.outputs["Color"], bsdf.inputs["Metallic"])
    nt.links.new(ro.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(no.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    o.data.materials.clear()
    o.data.materials.append(mat)


def outline_like(n, r_tip, thickness):
    """What build_preview_rig reads from a form's outline: n, r_tip, half_t, tip_extents()."""
    def tip_extents():
        xs = [r_tip * math.cos(2 * math.pi * k / n) for k in range(n)]
        ys = [r_tip * math.sin(2 * math.pi * k / n) for k in range(n)]
        return max(xs) - min(xs), max(ys) - min(ys)
    return SimpleNamespace(n=n, r_tip=r_tip, thickness=thickness, half_t=0.5 * thickness, tip_extents=tip_extents)


def run(tag, scale):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    before = set(bpy.data.objects)
    bpy.ops.wm.fbx_import(filepath=str(REF / "shuriken_lp.fbx"))
    objs = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    o = objs[0]
    for other in objs[1:]:
        bpy.data.objects.remove(other)
    o.scale = (scale, scale, scale)
    bpy.context.view_layer.update()
    w = world_verts(o)
    c = (w.max(0) + w.min(0)) / 2
    o.location = o.location - Vector(c)
    bpy.context.view_layer.update()
    w = world_verts(o)
    span = w.max(0) - w.min(0)
    r_tip = float(np.hypot(w[:, 0], w[:, 1]).max())
    thickness = float(span[2])
    idx = int(np.argmax(np.hypot(w[:, 0], w[:, 1])))            # arm 0 to +X like the pack's forms
    ang = math.atan2(w[idx, 1], w[idx, 0])
    o.rotation_euler = (o.rotation_euler[0], o.rotation_euler[1], o.rotation_euler[2] - ang)
    bpy.context.view_layer.update()
    textured_material(o)
    outline = outline_like(6, r_tip, thickness)
    info = {"tag": tag, "scale": scale, "span_mm": [round(float(v) * 1000, 2) for v in span],
            "r_tip_mm": round(r_tip * 1000, 2), "thickness_mm": round(thickness * 1000, 3), "samples": SAMPLES}

    R.setup_render(SAMPLES, RES_X, RES_Y)
    frame = R.TOP_FRAME_HEIGHT
    if max(outline.tip_extents()) > 0.92 * R.TOP_FRAME_HEIGHT:
        R.TOP_FRAME_HEIGHT = max(outline.tip_extents()) / 0.83
        info["top_frame_patched_mm"] = round(R.TOP_FRAME_HEIGHT * 1000, 1)
    try:
        rig = R.build_preview_rig(outline, RES_X, RES_Y, 1.0)
    finally:
        R.TOP_FRAME_HEIGHT = frame
    wall_mask = R._wall_mask_material()
    view_layer = bpy.context.view_layer

    def shoot(name, camera, lights, card, band):
        for light in rig["hero_lights"] + rig["top_lights"]:
            light.hide_render = light not in lights
        rig["ground"].hide_render = False
        rig["card"].hide_render = not card
        rig["band"].hide_render = not band
        scene.render.film_transparent = False
        scene.cycles.samples = SAMPLES
        scene.cycles.use_denoising = True
        beauty = Path(R.render_to(HERE / f"{name}.png", camera))
        rig["ground"].hide_render = True
        rig["card"].hide_render = True
        rig["band"].hide_render = True
        scene.render.film_transparent = True
        scene.cycles.samples = max(8, SAMPLES // 12)
        vt = scene.view_settings.view_transform
        view_layer.material_override = wall_mask
        scene.view_settings.view_transform = "Standard"
        try:
            mask = Path(R.render_to(HERE / f"{name}_mask.png", camera))
        finally:
            view_layer.material_override = None
            scene.view_settings.view_transform = vt
            scene.render.film_transparent = False
        return R.image_stats(beauty, mask, 6)

    R.fit_perspective(rig["cam_persp"], [o], 0.90, 0.86)
    R.centre_perspective(rig["cam_persp"], [o], RES_X, RES_Y)
    R.solve_depth_of_field(rig["cam_persp"], [o], RES_X)
    info["hero"] = shoot(f"ref_rig_{tag}_persp", rig["cam_persp"], rig["hero_lights"], True, False)
    info["top"] = shoot(f"ref_rig_{tag}_top", rig["cam_top"], rig["top_lights"], False, True)
    info["gates"] = {"hero_walls": R.wall_gate(info["hero"]), "hero_facets_near": R.facet_gate(info["hero"], "near"),
                     "hero_plate": R.plate_gate(info["hero"]), "top_facets": R.facet_gate(info["top"], "all"),
                     "top_plate": R.plate_gate(info["top"])}
    return info


results = {"rig": "shuriken_lib.render (the pack's gallery rig, unchanged)", "resolution": [RES_X, RES_Y],
           "bands": {"PLATE_BAND": list(R.PLATE_BAND), "PLATE_MEAN_BAND": list(R.PLATE_MEAN_BAND)}}
for tag, scale in (("scaled100", 100.0 / 197.0), ("native197", 1.0)):
    try:
        results[tag] = run(tag, scale)
    except Exception as exc:  # keep going, report the failure
        import traceback
        results[tag] = {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()}
    print("REFRIG", tag, json.dumps({k: v for k, v in results[tag].items() if k in ("span_mm", "error", "top_frame_patched_mm")}))
    for shot in ("hero", "top"):
        s = results[tag].get(shot)
        if s:
            print("REFRIG", tag, shot, json.dumps(s.get("object_luminance")), "walls",
                  json.dumps((s.get("wall_luminance") or {}).get("p50")), "facets",
                  json.dumps({k: v.get("p50") for k, v in (s.get("facet_luminance") or {}).items() if isinstance(v, dict)}))
(HERE / "ref_rig_stats.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
print("REFRIG_DONE", HERE / "ref_rig_stats.json")
