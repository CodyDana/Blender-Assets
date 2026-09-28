"""The grind-extent decision's evidence: arm 0's hook, close up, through the pack rig's hero lamps (headless).

Two modes, both READ ONLY on the project (nothing under Assets / Exports / Renders is written):

    # 1. author variant B (the photo-length grind: the chamfer resumes 20 mm from the tip on both blade edges) into a
    #    scratch .blend - the pack's own build_form path, no export / bake / render
    blender -b --factory-startup --python grind_extent_compare.py -- build-b <scratch.blend>

    # 2. render the close-ups of whichever .blend is open (A = the shipped Assets/Shuriken.blend, B = the scratch one):
    #    only SM_Shuriken_HookedCross_LOD0 is visible, with M_Shuriken_Master (the bake source) and the pack's hero lamps,
    #    ground and wall card (shuriken_lib.render.build_preview_rig); every camera looks down on +Z
    blender -b <file.blend> --python grind_extent_compare.py -- closeup <out_prefix>

Then  py -3 grind_extent_compare.py sheet <a_prefix> <b_prefix> <out.png>  lays A and B side by side.
"""
import sys
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
VIEWS = [(55.0, -10.0, 0.11, 70.0), (30.0, -35.0, 0.12, 70.0)]     # (elevation, azimuth, distance m, lens mm)
TARGET = (38.8e-3, 13.5e-3, 0.0)                                    # the middle of arm 0's hook


def build_b(out_blend: str) -> None:
    from dataclasses import replace
    sys.path.insert(0, str(PROJ / "Scripts" / "shuriken"))
    import build_hooked_cross as B
    from shuriken_lib.outline_plate import OutlinePlateGeometry
    from shuriken_lib.pack import BuildOptions, Form, build_form, reset_scene
    from shuriken_lib.material import build_material
    import bpy
    spec = replace(B.SPEC, back_grind_end_mm=20.0, inner_grind_end_mm=20.0)
    form = Form(spec=spec, module_path=str(B.HERE), annotate=None, geometry=OutlinePlateGeometry(spec))
    reset_scene()
    material = build_material()
    build_form(form, material, BuildOptions(no_export=True, no_render=True, no_bake=True))
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    print("VARIANT_B_SAVED", out_blend)


def closeup(prefix: str) -> None:
    import bpy
    prefix = str(Path(prefix).resolve())          # absolute: Blender resolves a relative render path at the drive root
    from mathutils import Vector
    sys.path.insert(0, str(PROJ / "Scripts" / "shuriken"))
    import build_hooked_cross as B
    from shuriken_lib import render as R
    from shuriken_lib.outline_plate import OutlineRenderInfo
    info = OutlineRenderInfo(B.SPEC.outline())
    for ob in bpy.data.objects:
        ob.hide_render = ob.name != "SM_Shuriken_HookedCross_LOD0"
    R.setup_render(128, 1200, 900)
    rig = R.build_preview_rig(info, 1200, 900)
    for lamp in rig["hero_lights"]:
        lamp.hide_render = False
        lamp.visible_camera = False
    rig["ground"].hide_render = False
    rig["card"].hide_render = False
    data = bpy.data.cameras.new("CamHook")
    data.clip_start = 0.005                       # the default 0.1 m clips the floor right under an 0.11 m close-up
    cam = bpy.data.objects.new("CamHook", data)
    rig["collection"].objects.link(cam)
    target = Vector(TARGET)
    for i, (el, az, dist, lens) in enumerate(VIEWS):
        data.lens = lens
        cam.location = target + Vector(R._polar(dist, el, az))
        R._aim(cam, target)
        side = R.camera_side(cam, info.half_t)
        assert side["sees"] == "+Z", side
        R.render_to(Path(f"{prefix}_{i}.png"), cam)
    print("CLOSEUP_DONE", prefix)


def sheet(a_prefix: str, b_prefix: str, out: str) -> None:
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 30)
    rows = []
    for i in range(len(VIEWS)):
        a = Image.open(f"{a_prefix}_{i}.png").convert("RGB")
        b = Image.open(f"{b_prefix}_{i}.png").convert("RGB")
        w, h = a.size
        row = Image.new("RGB", (2 * w, h))
        row.paste(a, (0, 0))
        row.paste(b, (w, 0))
        d = ImageDraw.Draw(row)
        d.text((20, 18), "A (built): the whole blade - runs out at the shoulder / the hook-corner fillet", font=font,
               fill=(255, 225, 90))
        d.text((w + 20, 18), "B (rejected): 20 mm from the tip + 3 mm run-out (photo facet ~17 mm)", font=font,
               fill=(255, 225, 90))
        rows.append(row)
    img = Image.new("RGB", (rows[0].size[0], sum(r.size[1] for r in rows)))
    y = 0
    for r in rows:
        img.paste(r, (0, y))
        y += r.size[1]
    img.save(out)
    print("SHEET", out, img.size)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if args[0] == "build-b":
        build_b(args[1])
    elif args[0] == "closeup":
        closeup(args[1])
    elif args[0] == "sheet":
        sheet(args[1], args[2], args[3])
