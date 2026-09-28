"""FINALISE: recolour swatches of the flashbang IN UNREAL (real RHI: -AllowCommandletRendering -RenderOffscreen).

Reads the pack build's assets (/Game/NinjaPack: SM_Flashbang with MI_Flashbang_Paint / MI_Flashbang_Steel assigned by
run_build.sh 'assign'); saves nothing.  For each colour a MaterialInstanceDynamic of MI_Flashbang_Paint overrides only
'Colour' (what a buyer edits), and a lit three-quarter frame is captured with the pack's own beauty rig
(np_render.setup_lights / _capture / _export, used read-only).  Also the default instance (no override) for reference.
Output: WorkFiles/flashbang/fin/ue_swatches/*.png + swatches.json.
"""
import json
import math
import sys
import traceback
from pathlib import Path

sys.dont_write_bytecode = True
PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(PROJ / "Scripts" / "unreal" / "materials"))
import unreal  # noqa: E402
import np_render as R  # noqa: E402

OUT = PROJ / "WorkFiles" / "flashbang" / "fin" / "ue_swatches"
OUT.mkdir(parents=True, exist_ok=True)


def s2l(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


COLOURS = {"default": None, "black_1C1C1C": "1C1C1C", "desert_B89B6A": "B89B6A", "navy_22304A": "22304A",
           "red_8E2020": "8E2020", "grey_7A7D80": "7A7D80", "white_EDEDE8": "EDEDE8"}
rep = {"engine": unreal.SystemLibrary.get_engine_version(), "frames": {}}
try:
    w = R.world()
    mesh = unreal.load_asset("/Game/NinjaPack/Meshes/SM_Flashbang")
    paint = unreal.load_asset("/Game/NinjaPack/MaterialInstances/MI_Flashbang_Paint")
    rep["mesh"] = mesh.get_path_name() if mesh else None
    rep["paint_instance"] = paint.get_path_name() if paint else None
    lights, rig = R.setup_lights(w, R.DEFAULT_LIGHT_SCALE)
    rep["rig"] = rig
    actor = R.EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0), R.rot(yaw=-30.0))
    smc = actor.get_editor_property("static_mesh_component")
    smc.set_static_mesh(mesh)
    b = mesh.get_bounds()
    zmin = b.origin.z - b.box_extent.z
    floor = R.EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(b.origin.x, b.origin.y, zmin - 0.05), R.rot())
    fsm = floor.get_editor_property("static_mesh_component")
    fsm.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
    fsm.set_material(0, unreal.load_asset(R.FLOOR_MATERIAL))
    s_ = max(float(b.sphere_radius) * 20.0 / 100.0, 1.0)
    floor.set_actor_scale3d(unreal.Vector(s_, s_, 1.0))
    centre = b.origin
    radius = float(b.sphere_radius)
    fov = 20.0
    dist = radius / math.sin(math.radians(fov / 2.0)) * 1.05
    yaw, elev = 215.0, 14.0                       # the pack rig's lit side (its "low" beauty view)
    loc = unreal.Vector(centre.x + dist * math.cos(math.radians(elev)) * math.cos(math.radians(yaw)),
                        centre.y + dist * math.cos(math.radians(elev)) * math.sin(math.radians(yaw)),
                        centre.z + dist * math.sin(math.radians(elev)))
    cam_rot = R._look_at(loc, centre)
    for name, hexc in COLOURS.items():
        rec = {"hex": hexc}
        try:
            if hexc is None:
                smc.set_material(0, paint)
            else:
                mid = unreal.MaterialLibrary.create_dynamic_material_instance(w, paint, f"sw_{name}")
                lin = [s2l(int(hexc[i:i + 2], 16)) for i in (0, 2, 4)]
                mid.set_vector_parameter_value("Colour", unreal.LinearColor(*lin, 1.0))
                rec["colour_linear"] = [round(x, 6) for x in lin]
                smc.set_material(0, mid)
            cap, cc, rt = R._capture(w, 1024, 1024, unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR,
                                     unreal.TextureRenderTargetFormat.RTF_RGBA8, loc, cam_rot, fov=fov, bias=0.0)
            try:
                for _ in range(3):
                    cc.capture_scene()
                rec["png"] = R._export(w, rt, OUT, f"swatch_{name}.png")
            finally:
                R.EAS.destroy_actor(cap)
        except Exception:  # noqa: BLE001
            rec["error"] = traceback.format_exc()[-1200:]
        rep["frames"][name] = rec
    for a in [actor, floor] + list(lights):
        try:
            R.EAS.destroy_actor(a)
        except Exception:  # noqa: BLE001
            pass
    rep["passed"] = all("png" in v for v in rep["frames"].values())
except Exception:  # noqa: BLE001
    rep["error"] = traceback.format_exc()
(OUT / "swatches.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
unreal.log("FBF_SWATCH_DONE")
