import re
from pathlib import Path
src = Path("landscape/verify/v10_ue_boundary.py").read_text(encoding="utf-8")
def sw(a, b, n=1):
    global src
    assert src.count(a) == n, (a[:80], src.count(a))
    src = src.replace(a, b)
src = '''# HALL + ARMORY VERIFIER (independent): the landscape verifier's v10 boundary script for the extended hall: the ring's
# north side at y 48.1 (FBX audit: local 0..49.2 at -1.1), the B-polygon's north edge at y 56 (world_layout_delta B6),
# the layout's 88 walk routes with MY walker v2 (CMC order: move flat first, step up only when blocked, the lift clamped
# under a ceiling such as the door head), MY interior walking flood (courtyard -> step band -> veranda -> doors ->
# interior), BR / 1v1 walks over the new rear roof, the stair after the lantern move, flood1v1 / floodbr / arcs1v1.
''' + src
src = re.sub(r"^VD = Path\(.*$", 'VD = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/hall_armory/verify/json")', src, count=1, flags=re.M)
sw("RINGF = (-1.1, 45.1, -1.1, 37.1)", "RINGF = (-1.1, 45.1, -1.1, 48.1)")
sw("return (-7.0 < x < 48.75 and -2.75 < y < 44.0) or (12.2 < x < 34.25 and -7.75 < y <= -2.75)",
   "return (-7.0 < x < 48.75 and -2.75 < y < 56.0) or (12.2 < x < 34.25 and -7.75 < y <= -2.75)")
sw("segs = [((-7, -2.75), (-7, 44)), ((-7, 44), (48.75, 44)), ((48.75, 44), (48.75, -2.75)),",
   "segs = [((-7, -2.75), (-7, 56)), ((-7, 56), (48.75, 56)), ((48.75, 56), (48.75, -2.75)),")
sw("pts = surfaces((-1.0, 45.0), (-1.0, 37.0), 0.25, IGN[\"br\"], lambda x, y, z: in_ring(x, y))",
   "pts = surfaces((-1.0, 45.0), (-1.0, 48.0), 0.25, IGN[\"br\"], lambda x, y, z: in_ring(x, y))")
sw("pts = surfaces((-1.0, 45.0), (-1.0, 37.0), 0.5, IGN[\"br\"], keep)", "pts = surfaces((-0.95, 45.0), (-0.95, 48.0), 0.45, IGN[\"br\"], keep)")
sw("pts = surfaces((-7.0, 48.75), (-7.75, 44.0), 0.5, IGN[\"bonly\"], keep)", "pts = surfaces((-7.0, 48.75), (-7.75, 56.0), 0.5, IGN[\"bonly\"], keep)")
sw("rep = {\"verifier\": \"independent landscape round\"", "rep = {\"verifier\": \"independent hall+armory v11\"")
sw("unreal.log(f\"V10B_BOUNDARY_DONE", "unreal.log(f\"VHA_BOUNDARY_DONE")
# routes use walker v2
sw("        res = walk([tuple(p) for p in rt[\"points\"]], 30.0, ign, rt[\"floor_z\"])",
   "        res = walk2([tuple(p) for p in rt[\"points\"]], 30.0, ign, rt[\"floor_z\"])\n        res35 = walk2([tuple(p) for p in rt[\"points\"]], 35.0, ign, rt[\"floor_z\"])\n        res[\"clear_r35\"] = res35[\"clear\"]")
# insert new parts before main()
new = Path("hall_armory/verify/v11_boundary_extra.py").read_text(encoding="utf-8")
i = src.index("def main():")
src = src[:i] + new + "\n\n" + src[i:]
sw('''        if "stair" in PARTS:''', '''        if "interior" in PARTS:
            rep["interior"] = run_interior()
            unreal.log(f"VHA_INTERIOR reached {rep['interior'].get('reached_cells')} leaks {rep['interior'].get('leaks_into_targets')}")
            save()
        if "rearroof" in PARTS:
            rep["rearroof"] = run_rearroof()
            unreal.log(f"VHA_REARROOF {rep['rearroof'].get('summary')}")
            save()
        if "stair" in PARTS:''')
Path("hall_armory/verify/v11_ue_boundary.py").write_text(src, encoding="utf-8")
print("ok")
