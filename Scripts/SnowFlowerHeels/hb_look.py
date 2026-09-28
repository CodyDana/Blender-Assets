"""Studio look renders in the reference camera (Cycles): white ground, soft key/fill/rim, shadow catcher.

    blender -b --factory-startup --python Scripts/SnowFlowerHeels/hb_look.py -- <tag> <parts npz> [--samples 96]

Uses the high-poly procedural shading (hb_d_assemble.MATS + grain) - a PREVIEW of the design; the deliverable renders
use the baked game mesh (hb_g_render.py).
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hb_common as C  # noqa: E402
import hb_camrender as CR  # noqa: E402


def principled(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def make_mat(name, col, met, rough, coat=0.0, bump=None, bump_scale=1.0, bump_str=0.2):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = principled(m)
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Metallic"].default_value = met
    b.inputs["Roughness"].default_value = rough
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.04
    if bump:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        if bump == "noise":
            tx = nt.nodes.new("ShaderNodeTexNoise")
            tx.inputs["Scale"].default_value = bump_scale
            tx.inputs["Detail"].default_value = 8
            out = tx.outputs["Fac"]
        else:
            tx = nt.nodes.new("ShaderNodeTexVoronoi")
            tx.feature = "DISTANCE_TO_EDGE"
            tx.inputs["Scale"].default_value = bump_scale
            out = tx.outputs["Distance"]
        nt.links.new(tc.outputs["Object"], tx.inputs["Vector"])
        bn = nt.nodes.new("ShaderNodeBump")
        bn.inputs["Strength"].default_value = bump_str
        bn.inputs["Distance"].default_value = 0.0002
        nt.links.new(out, bn.inputs["Height"])
        nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    return m


def studio(scene, samples=96):
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
    except Exception:  # noqa: BLE001
        pass
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    w = bpy.data.worlds.new("studio")
    scene.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    # soft grey studio with a brighter top (gradient via light path is overkill: use a sky-ish sphere gradient)
    tc = w.node_tree.nodes.new("ShaderNodeTexCoord")
    sep = w.node_tree.nodes.new("ShaderNodeSeparateXYZ")
    ramp = w.node_tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.18, 0.18, 0.18, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    mp = w.node_tree.nodes.new("ShaderNodeMapRange")
    mp.inputs["From Min"].default_value = -1
    mp.inputs["From Max"].default_value = 1
    w.node_tree.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    w.node_tree.links.new(sep.outputs["Z"], mp.inputs["Value"])
    w.node_tree.links.new(mp.outputs["Result"], ramp.inputs["Fac"])
    w.node_tree.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.55


def add_light(name, loc, target, power, size):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = power
    ld.size = size
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def lights_for_cam(cam_basis, center):
    cdir, right, up = cam_basis
    c = Vector(center)
    key = c + Vector(cdir) * 0.5 - Vector(right) * 0.35 + Vector((0, 0, 0.6))
    fill = c + Vector(cdir) * 0.6 + Vector(right) * 0.5 + Vector((0, 0, 0.15))
    rim = c - Vector(cdir) * 0.6 + Vector((0, 0, 0.5))
    top = c + Vector((0, 0, 0.9))
    add_light("key", key, c, 3.0, 0.6)
    add_light("fill", fill, c, 1.0, 0.8)
    add_light("rim", rim, c, 2.0, 0.5)
    add_light("top", top, c, 1.5, 0.8)


def shadow_catcher():
    bpy.ops.mesh.primitive_plane_add(size=3.0, location=(0.1, 0, 0))
    p = bpy.context.active_object
    p.is_shadow_catcher = True
    return p


def composite_white(render_png, out_png, tag_png=None):
    import metro_png as png
    ren = png.read(str(render_png)).astype(float)
    ren = ren / 255.0 if ren.max() > 1.5 else ren
    a = ren[..., 3:4]
    rgb = ren[..., :3] * a + (1 - a) * 1.0
    png.write(str(out_png), (np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    return rgb


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    tag, npz = argv[0], argv[1]
    samples = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 96
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    studio(sc, samples)
    mats = {
        "leather": make_mat("leather", (0.009, 0.0085, 0.008), 0, 0.42, bump="noise", bump_scale=2500, bump_str=0.25),
        "lining": make_mat("lining", (0.004, 0.004, 0.004), 0, 0.8),
        "binding": make_mat("binding", (0.016, 0.015, 0.015), 0, 0.42),
        "crackle": make_mat("crackle", (0.035, 0.033, 0.032), 0, 0.45, bump="voronoi", bump_scale=450, bump_str=0.5),
        "strap": make_mat("strap", (0.014, 0.013, 0.013), 0, 0.38, bump="noise", bump_scale=2500, bump_str=0.1),
        "sole": make_mat("sole", (0.012, 0.011, 0.011), 0, 0.3),
        "insole": make_mat("insole", (0.035, 0.034, 0.033), 0, 0.6),
        "silver": make_mat("silver", (0.62, 0.58, 0.55), 1, 0.24, bump="noise", bump_scale=900, bump_str=0.05),
        "silver_recess": make_mat("silver_recess", (0.16, 0.145, 0.135), 1, 0.45),
        "pearl": make_mat("pearl", (0.62, 0.58, 0.55), 0, 0.32, coat=0.5),
        "patent": make_mat("patent", (0.005, 0.005, 0.005), 0, 0.08, coat=1.0),
    }
    z = np.load(npz)
    for n in sorted({k[:-2] for k in z.files if k.endswith("_v")}):
        faces = []
        for suf in ("_q", "_t"):
            if n + suf in z.files and len(z[n + suf]):
                faces += z[n + suf].tolist()
        me = bpy.data.meshes.new(n)
        me.from_pydata([tuple(map(float, p * 0.001)) for p in z[n + "_v"]], [], [tuple(map(int, f)) for f in faces])
        me.update()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(mats.get(n, mats["leather"]))
        ob = bpy.data.objects.new(n, me)
        sc.collection.objects.link(ob)
        ob.modifiers.new("ws", "WEIGHTED_NORMAL").keep_sharp = True
    cam = CR.load_cam()
    CR.setup_camera(cam, np.diag([0.001, 0.001, 0.001, 1.0]))
    lights_for_cam(cam.basis(), (0.11, 0.0, 0.1))
    shadow_catcher()
    out = C.R1 / "preview"
    rp = out / f"{tag}_look_rgba.png"
    sc.render.filepath = str(rp)
    bpy.ops.render.render(write_still=True)
    composite_white(rp, out / f"{tag}_look.png")
    CR.composite(out / f"{tag}_look.png", out / f"{tag}_lookcmp.png")
    print("LOOK_OK", out / f"{tag}_lookcmp.png")


if __name__ == "__main__":
    main()
