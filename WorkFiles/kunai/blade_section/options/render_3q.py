"""The 3/4 diagonal pose of Renders/Shuriken/kunai_plain_3q.png, for one blade-section option, plus its coat statistics.

Reproduces the main chat's reviewer shot c07_whole_3q (closeups.py, 2026-09-19): the pack's own gallery rig
(render.setup_render + build_preview_rig, hero lamps scaled by the hero's rig scale 2.724318), the kunai turned
yaw +40 deg about Z, a 72 mm lens at elevation 29 / azimuth -22 deg aimed at the shoulder (design x 0), 320 mm framed
across 1600 x 900, 160 samples, the option's own baked maps (steel BC/ORM/N + wrap maps).  Then a mask pass
(render._wall_mask_material, 8 samples, Standard) and render.image_stats - the same statistics the build's hero gate
reads - so the coat p50 / mean of each option in the 3/4 pose can be compared with PACK_COAT_ANCHOR.

Imports shuriken_lib from the PROTOTYPE tree (options/proto_tree), never from Scripts/.  Opens the option's blend
read-only (it is never saved).  Usage:
  blender -b <option.blend> --factory-startup --python render_3q.py -- <report.json> <out_dir> [samples] [yaw ...]
"""
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
for p in (HERE / "proto_tree" / "Scripts" / "shuriken", HERE / "proto_tree" / "Scripts"):
    sys.path.insert(0, str(p))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from shuriken_lib import render as R  # noqa: E402
from shuriken_lib.bake import preview_material  # noqa: E402
from shuriken_lib.kunai_wrap import wrap_preview_material  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
report = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
out = Path(argv[1])
out.mkdir(parents=True, exist_ok=True)
samples = int(argv[2]) if len(argv) > 2 else 160
poses = argv[3:] or ["3q:40"]
MM = 0.001
RES = (1600, 900)
RIG_SCALE = 2.724318
shift = float(report["measured"]["pivot_design_x_mm"])


def ox(design_x_mm):
    return (design_x_mm - shift) * MM


class O:                               # KunaiRenderInfo, as the rig reads it (kunai.py 3.10.1)
    n = 2
    half_t = 10.0 * MM
    x_tip = ox(140.0)
    x_butt = ox(-140.0)
    r_tip = x_tip
    top_frame_height = 0.18
    top_centre_xy = (0.5 * (x_tip + x_butt), 0.0)
    wrap_mask = True
    a = 2.5 * MM

    def tip_extents(self):
        return self.x_tip - self.x_butt, 36.0 * MM


scene = bpy.context.scene
lod0 = bpy.data.objects["SM_Kunai_Plain_LOD0"]
for ob in bpy.data.objects:
    ob.hide_render = ob is not lod0
R.setup_render(samples, *RES)
o = O()
rig = R.build_preview_rig(o, RES[0], RES[1])
for light in rig["hero_lights"]:
    light.location = light.location * RIG_SCALE
    light.data.size *= RIG_SCALE
    light.data.size_y *= RIG_SCALE
    light.data.energy *= RIG_SCALE ** 2
tex = report["textures"]
steel = preview_material("M_3Q_Steel", tex["maps"], uv_map=tex["uv_map"])
wrapm = wrap_preview_material(tex)
lod0.data.materials[0] = steel
lod0.data.materials[1] = wrapm
mask_mat = R._wall_mask_material()


def orient_mask_material():
    """Red = 1 on FLAT faces (|N.z| >= 0.9995 = within 1.8 deg of flat, true normal: the anchor plates' own orientation - the ring flats, the
    neck plateau); green = 1 on the other coat-class faces (0.95 <= |N.z| < 0.9995: the tilted diamond faces)."""
    mat = bpy.data.materials.new("M_3Q_OrientMask")
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    out_n = t.nodes.new("ShaderNodeOutputMaterial")
    geom = t.nodes.new("ShaderNodeNewGeometry")
    sep = t.nodes.new("ShaderNodeSeparateXYZ")
    absz = t.nodes.new("ShaderNodeMath"); absz.operation = "ABSOLUTE"
    flat = t.nodes.new("ShaderNodeMath"); flat.operation = "GREATER_THAN"; flat.inputs[1].default_value = 0.9995
    coat = t.nodes.new("ShaderNodeMath"); coat.operation = "GREATER_THAN"; coat.inputs[1].default_value = 0.95
    tilt = t.nodes.new("ShaderNodeMath"); tilt.operation = "SUBTRACT"
    comb = t.nodes.new("ShaderNodeCombineColor")
    emit = t.nodes.new("ShaderNodeEmission")
    t.links.new(geom.outputs["True Normal"], sep.inputs["Vector"])
    t.links.new(sep.outputs["Z"], absz.inputs[0])
    t.links.new(absz.outputs["Value"], flat.inputs[0])
    t.links.new(absz.outputs["Value"], coat.inputs[0])
    t.links.new(coat.outputs["Value"], tilt.inputs[0])
    t.links.new(flat.outputs["Value"], tilt.inputs[1])
    t.links.new(flat.outputs["Value"], comb.inputs["Red"])
    t.links.new(tilt.outputs["Value"], comb.inputs["Green"])
    t.links.new(comb.outputs["Color"], emit.inputs["Color"])
    t.links.new(emit.outputs["Emission"], out_n.inputs["Surface"])
    return mat


orient_mat = orient_mask_material()


def reference_coat_material():
    """The pack's nominal coat as a UNIFORM material (material.py COAT, metallic 1, COAT_ROUGHNESS): rendered on the
    SAME geometry in the SAME pose it cancels the geometry and the light, so baked-minus-reference isolates the finish."""
    from shuriken_lib.material import COAT, COAT_ROUGHNESS
    mat = bpy.data.materials.new("M_3Q_RefCoat")
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*COAT, 1.0)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = COAT_ROUGHNESS
    return mat


ref_mat = reference_coat_material()


def lum_stats(values):
    import numpy as np
    if values.size == 0:
        return None
    return {"pixels": int(values.size), "mean": round(float(values.mean()), 4),
            "p05": round(float(np.percentile(values, 5)), 4), "p50": round(float(np.percentile(values, 50)), 4),
            "p95": round(float(np.percentile(values, 95)), 4)}

cam_data = bpy.data.cameras.new("C3Q_Cam")
cam = bpy.data.objects.new("C3Q_Cam", cam_data)
scene.collection.objects.link(cam)
cam_data.dof.use_dof = False
cam_data.clip_start = 0.005
cam_data.lens = 72.0
cam_data.sensor_width = 36.0


def polar_dir(el, az):
    e, a = math.radians(el), math.radians(az)
    return Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))


results = {}
base_lamps = [(l, l.location.copy(), l.data.size, l.data.size_y, l.data.energy) for l in rig["hero_lights"]]
for pose in poses:
    kind, _, yaw = pose.partition(":")
    yaw = float(yaw)
    for l, loc, size, size_y, energy in base_lamps:           # the 3q rig (hero lamps x 2.724318)
        l.location, l.data.size, l.data.size_y, l.data.energy = loc.copy(), size, size_y, energy
    lod0.location = (0.0, 0.0, 0.0)
    lod0.rotation_euler = (0.0, 0.0, math.radians(yaw))
    bpy.context.view_layer.update()
    if kind == "3q":
        use_cam = cam
        target = lod0.matrix_world @ Vector((ox(0.0), 0.0, 0.0))
        d = 320.0 * MM * 72.0 / 36.0
        cam.location = target + polar_dir(29.0, -22.0) * d
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    elif kind == "top":                                       # the build's top (spec) view: ortho, top lamps, band
        use_cam = rig["cam_top"]
    else:                                                     # the build's gallery hero (render_previews, 3.8.1 path)
        use_cam = rig["cam_persp"]
        use_cam.location = R._polar(0.30, 29.0, -22.0)
        use_cam.data.shift_x = use_cam.data.shift_y = 0.0
        R._aim(use_cam)
        R.fit_perspective(use_cam, [lod0], 0.90, 0.86)
        R.centre_perspective(use_cam, [lod0], *RES)
        R.place_for_shift(use_cam, lod0, *RES)
        R.centre_perspective(use_cam, [lod0], *RES, steps=1)
        R.solve_depth_of_field(use_cam, [lod0], RES[0])
        k = use_cam.location.length / R.HERO_RIG_REFERENCE_M
        for l, loc, size, size_y, energy in base_lamps:
            l.location = (loc / RIG_SCALE) * k
            l.data.size, l.data.size_y, l.data.energy = size / RIG_SCALE * k, size_y / RIG_SCALE * k, energy / RIG_SCALE ** 2 * k * k
        bpy.context.view_layer.update()
    lamps = rig["top_lights"] if kind == "top" else rig["hero_lights"]
    for light in rig["hero_lights"] + rig["top_lights"]:
        light.hide_render = light not in lamps
    rig["ground"].hide_render = False
    rig["card"].hide_render = kind == "top"
    rig["band"].hide_render = kind != "top"
    scene.render.film_transparent = False
    scene.cycles.samples = samples
    name = f"kunai_{kind}_y{yaw:g}"
    beauty = Path(R.render_to(out / f"{name}.png", use_cam))
    rig["ground"].hide_render = True
    rig["card"].hide_render = True
    scene.render.film_transparent = True
    scene.cycles.samples = 8
    vt = scene.view_settings.view_transform
    bpy.context.view_layer.material_override = mask_mat
    scene.view_settings.view_transform = "Standard"
    mask = Path(R.render_to(out / f"{name}_mask.png", use_cam))
    bpy.context.view_layer.material_override = orient_mat
    omask = Path(R.render_to(out / f"{name}_orient.png", use_cam))
    bpy.context.view_layer.material_override = None
    scene.view_settings.view_transform = vt
    scene.render.film_transparent = False
    lod0.data.materials[0] = ref_mat
    scene.cycles.samples = samples
    ref_beauty = Path(R.render_to(out / f"{name}_refcoat.png", use_cam))
    lod0.data.materials[0] = steel
    st = R.image_stats(beauty, mask, o.n, wrap=True)
    import numpy as np
    px = R.load_pixels(beauty)[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    mk = R.load_pixels(mask)
    om = R.load_pixels(omask)
    sel = mk[..., 3] > 0.85
    coat_px = sel & (mk[..., 0] <= 0.5) & (mk[..., 1] <= 0.5) & (mk[..., 2] <= 0.5)
    flat_px = coat_px & (om[..., 0] > 0.5)
    tilt_px = coat_px & (om[..., 0] <= 0.5)
    split = {"flat_coat_nz_ge_0_9995": lum_stats(px[flat_px]), "tilted_coat_0_95_to_0_9995": lum_stats(px[tilt_px]),
             "all_coat": lum_stats(px[coat_px])}
    rpx = R.load_pixels(ref_beauty)[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    split["reference_coat"] = {"flat": lum_stats(rpx[flat_px]), "tilted": lum_stats(rpx[tilt_px]),
                               "all_coat": lum_stats(rpx[coat_px])}
    for key, m in (("flat", flat_px), ("tilted", tilt_px), ("all_coat", coat_px)):
        if m.any():
            split.setdefault("baked_minus_reference", {})[key] = {
                "p50": round(float(np.percentile(px[m], 50) - np.percentile(rpx[m], 50)), 4),
                "mean": round(float(px[m].mean() - rpx[m].mean()), 4),
                "ratio_mean": round(float(px[m].mean() / max(rpx[m].mean(), 1e-6)), 4)}
    results[name] = {"yaw_deg": yaw, "camera": {"el": 29.0, "az": -22.0, "lens_mm": 72.0, "framed_mm": 320.0,
                                                "target_design_x_mm": 0.0, "rig_scale": RIG_SCALE},
                     "samples": samples, "coat": st.get("coat_luminance"), "whole": st.get("object_luminance"),
                     "wrap": st.get("wrap_luminance"), "coat_gate": R.coat_gate(st),
                     "anchor_hero": R.PACK_COAT_ANCHOR["hero"], "coat_split": split, "stats": st,
                     "camera_used": {"location": list(use_cam.location), "lens": use_cam.data.lens,
                                     "shift": [use_cam.data.shift_x, use_cam.data.shift_y]}}
    c = st.get("coat_luminance") or {}
    print(f"C3Q {name}: coat p50 {c.get('p50')} mean {c.get('mean')} frac {c.get('fraction_of_object')} "
          f"dark {c.get('fraction_below_0_03')} | flat {split['flat_coat_nz_ge_0_9995']} | tilted {split['tilted_coat_0_95_to_0_9995']} | b-r {split.get('baked_minus_reference')}")
(out / "kunai_3q_stats.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
print("DONE")
