"""Placement / orientation proof of the kunai's lettering band with a NEUTRAL test mask (never shipped).

Opens the shipped Assets/Shuriken.blend read-only (nothing is saved), gives SM_Kunai_Plain_LOD0 the gallery's baked
preview materials - slot 0 the steel maps, slot 1 the wrap maps with T_Kunai_Lettering sampled through the band's UV
rectangle (shuriken_lib.kunai_wrap.wrap_preview_material, the same graph the Unreal material must build) - once with
the shipped BLANK mask and once with WorkFiles/kunai/lettering_test/T_Kunai_Lettering_TEST.png, and renders the grip
from straight above (+Z, tip to the right) and from a 3/4 view, with the pack's top / hero lamps.

    blender -b Assets/Shuriken.blend --factory-startup --python WorkFiles/kunai/lettering_test/lettering_test_render.py
"""
import json
import math
import sys
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(PROJ / "Scripts" / "shuriken"))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from shuriken_lib import render as R  # noqa: E402
from shuriken_lib.bake import preview_material  # noqa: E402
from shuriken_lib.kunai_wrap import wrap_preview_material  # noqa: E402

HERE = PROJ / "WorkFiles" / "kunai" / "lettering_test"
report = json.loads((PROJ / "WorkFiles" / "shuriken" / "kunai_plain_report.json").read_text(encoding="utf-8"))
tex = report["textures"]
shift = report["measured"]["pivot_design_x_mm"]
lod0 = bpy.data.objects["SM_Kunai_Plain_LOD0"]
for ob in bpy.data.objects:
    ob.hide_render = ob is not lod0
steel = preview_material("M_Test_Steel", tex["maps"], uv_map=tex["uv_map"])
blank = wrap_preview_material(tex, name="M_Test_Wrap_Blank")
test = wrap_preview_material(tex, lettering_path=str(HERE / "T_Kunai_Lettering_TEST.png"), name="M_Test_Wrap_Test")
lod0.data.materials[0] = steel

res_x, res_y = 1600, 900
R.setup_render(160, res_x, res_y)


class O:
    n = 2
    half_t = 0.0106
    r_tip = 0.2

    def tip_extents(self):
        return 0.1, 0.04


rig = R.build_preview_rig(O(), res_x, res_y)
rig["ground"].hide_render = True
rig["card"].hide_render = True
band_cx = (0.5 * (-90.0 + -18.0) - shift) * 0.001
cam_data = bpy.data.cameras.new("TEST_CamTop")
cam_data.type = "ORTHO"
cam_data.ortho_scale = 0.100
cam = bpy.data.objects.new("TEST_CamTop", cam_data)
rig["collection"].objects.link(cam)
cam.location = (band_cx, 0.0, 0.3)
cam.rotation_euler = (0.0, 0.0, 0.0)
cam3 = bpy.data.objects.new("TEST_Cam34", bpy.data.cameras.new("TEST_Cam34"))
rig["collection"].objects.link(cam3)
cam3.data.lens = 70.0
target = Vector((band_cx, 0.0, 0.0))
cam3.location = target + Vector((0.05, -0.16, 0.12))
R._aim(cam3, target)
shots = {}
for mat_name, mat in (("blank", blank), ("test", test)):
    lod0.data.materials[1] = mat
    for view, camera, lights in (("top", cam, rig["top_lights"]), ("34", cam3, rig["hero_lights"])):
        for light in rig["hero_lights"] + rig["top_lights"]:
            light.hide_render = light not in lights
        rig["ground"].hide_render = view == "top"
        path = HERE / f"lettering_{mat_name}_{view}.png"
        R.render_to(path, camera)
        shots[f"{mat_name}_{view}"] = str(path)
(HERE / "lettering_test_render.json").write_text(json.dumps({
    "shots": shots, "mask_test": str(HERE / "T_Kunai_Lettering_TEST.png"), "mask_shipped": tex["lettering"]["path"],
    "band_uv0_blender": tex["lettering_uv"]["uv0_blender"], "band_centre_object_x_m": band_cx,
    "note": "blank = the shipped mask (no ink, the band is plain clean tape); test = the neutral test pattern"},
    indent=2), encoding="utf-8")
print("LETTERING_TEST_DONE", shots)
