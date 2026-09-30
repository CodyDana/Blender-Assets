"""ROUND 5 review renders for the dressing track (Cycles, denoised, headless), from Assets/Dojo/DojoDressing.blend
(read-only: nothing is saved). Every context piece takes its kit's own TEXTURED mesh (dkd_common.textured_context);
the decals show as their ray-projected preview meshes (collection DecalPreview); the sunset rig is the round-4 review
renders' (render_sp.py). The real judgement is on the Unreal captures.

Run: blender -b --factory-startup Assets/Dojo/DojoDressing.blend --python Scripts/dojo/dressing/render_dressing.py --
     [--tag r0] [--samples 96] [--only a,b] [--no-decals] [--scale 1.0]
Out: WorkFiles/dojo/build/dressing/renders/<tag>/<view>.png (+ '_nodecals' with --no-decals), views.json
"""
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dkd_common as C  # noqa: E402

TAG = C.arg("--tag", "r0")
SAMPLES = int(C.arg("--samples", "96"))
ONLY = [s for s in C.arg("--only", "").split(",") if s]
NODECALS = "--no-decals" in C.args()
SCALE = float(C.arg("--scale", "1.0"))
OUT = C.RENDERS / TAG


def hfov_lens(hfov):
    return 18.0 / math.tan(math.radians(hfov) / 2)


LAYOUT = json.loads(C.SHOWCASE_LAYOUT.read_text(encoding="utf-8"))
LCAM = {c["name"]: c for c in LAYOUT["cameras"]}
# (name, loc, look, hfov, w, h, what it checks)
VIEWS = [
    ("EstablishingRef2", LCAM["CAM_EstablishingRef2"]["loc"], LCAM["CAM_EstablishingRef2"]["look_at"], 74, 1448, 1086,
     "reference 2's framing: the whole courtyard, hall gables in shade, wall feet, stair"),
    ("Overview", LCAM["CAM_Overview"]["loc"], LCAM["CAM_Overview"]["look_at"], 70, 1920, 1080,
     "reference 1's high view: roofs + wall caps (lichen), street wall foot"),
    ("GateFromStreet", LCAM["CAM_GateFromStreet"]["loc"], LCAM["CAM_GateFromStreet"]["look_at"], 64, 1920, 1080,
     "the gate plaque from the approach road"),
    ("CU_GatePlaque", (22.0, -4.3, 2.0), (22.0, -1.95, 2.98), 40, 1600, 900, "gate plaque close"),
    ("CU_HallGableW", (5.5, 21.5, 1.7), (14.5, 29.0, 7.6), 44, 1600, 900, "west hall gable plaque from the west yard"),
    ("CU_HallGablePlaque", (10.2, 26.2, 6.4), (14.5, 29.0, 7.93), 26, 1600, 900, "hall plaque close (roof level)"),
    ("EastYard", LCAM["CAM_EastYard"]["loc"], LCAM["CAM_EastYard"]["look_at"], 84, 1920, 1080,
     "east gable plaque, well, lantern, residence"),
    ("CU_WallFooting", LCAM["CU_WallFooting"]["loc"], LCAM["CU_WallFooting"]["look_at"], 56, 1600, 900,
     "moss + damp at the south wall foot, rain streaks under the cap"),
    ("CU_WestWall", (6.2, 11.2, 1.6), (0.0, 8.8, 0.9), 60, 1600, 900, "west wall: moss foot, streaks"),
    ("CU_StreetWall", (7.6, -6.6, 1.6), (11.5, -1.0, 0.9), 60, 1600, 900, "street face of the south wall"),
    ("CU_PathStepBand", LCAM["CU_PathStepBand"]["loc"], LCAM["CU_PathStepBand"]["look_at"], 58, 1600, 900,
     "worn gravel beside the stair, grime at the veranda posts and main doors"),
    ("CU_Lantern", LCAM["CU_Lantern"]["loc"], LCAM["CU_Lantern"]["look_at"], 44, 1600, 900, "lichen on the lantern"),
    ("CU_Downpipe", (8.2, 19.4, 1.5), (11.0, 22.4, 0.25), 55, 1600, 900, "water stain under the hall's SW downpipe"),
    ("CU_RoofLichen", (21.0, 15.5, 7.8), (17.0, 22.5, 3.3), 50, 1600, 900, "lichen on the hall's lower roof"),
    ("CU_Storehouse", LCAM["CU_R4_StorehouseFront"]["loc"], LCAM["CU_R4_StorehouseFront"]["look_at"], 70, 1600, 900,
     "streaks under the storehouse eave corners, door threshold grime"),
    ("CU_GateCourtyard", (22.0, 5.6, 1.6), (22.0, 0.0, 1.0), 62, 1600, 900, "gate posts grime, worn gravel by the apron"),
]


def main():
    for name in ("Kit",):
        c = bpy.data.collections.get(name)
        if c:
            c.hide_render = True
    dp = bpy.data.collections.get("DecalPreview")
    if dp:
        dp.hide_render = NODECALS
        dp.hide_viewport = False
    C.textured_context()
    C.setup_cycles(SAMPLES)
    C.sunset_rig()
    C.ground_plane(z=-0.25)
    done = {}
    for name, loc, look, hfov, w, h, what in VIEWS:
        if ONLY and name not in ONLY:
            continue
        cam = C.persp_cam("CAM_" + name, loc, look, hfov_lens(hfov))
        fn = f"{name}{'_nodecals' if NODECALS else ''}.png"
        C.render(cam, OUT / fn, int(w * SCALE), int(h * SCALE))
        done[fn] = {"loc": list(loc), "look": list(look), "hfov": hfov, "what": what}
    vj = OUT / "views.json"
    old = json.loads(vj.read_text(encoding="utf-8")) if vj.exists() else {}
    old.update(done)
    C.write_json(vj, old)


main()
