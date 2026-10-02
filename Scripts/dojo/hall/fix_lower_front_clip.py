"""HALL + ARMORY FIX round (2026-10-01): SM_DKH_RoofLower_Front rebuilt with its wall-flashing / rafter ends clipped at
the front wall, so nothing pokes through the INNER face of the hall's front wall (now seen from the armory interior).

Measured (WorkFiles/dojo/build/hall_armory/fix/blender/probe_front_wall.py on the shipped FBX): 94 vertices of the lower
front roof (the 0.09 m wide rafter ends / flashing tongues on the 0.30 m rafter pitch) stand at world y 24.0545,
z 3.926, i.e. 9.5 mm past the transom plaster's inner face (y 24.045): the row of dark dashes on the upper plaster panels
in CAM_AK_CX_FromPlatform (judge delta 3). Nothing else of the hall crosses that face between the head beam and the
plate (Frame_Open, VerandaFrame, RoofUpper_Front: 0 vertices).

Method (the hall builder stays the source; nothing is hand-edited in the FBX):
1. build the piece with Scripts/dojo/hall/build_hall.py's own roof_pieces() (read-only import, same roof_kit);
2. PROVE the rebuild reproduces the shipped mesh: import the shipped FBX and compare every render vertex (nearest
   neighbour both ways, max deviation must be <= 0.5 mm, same vertex count); abort otherwise;
3. clamp every render vertex with world y > CLIP_Y inside the wall band z 3.80-4.10 to y = CLIP_Y (24.040: 5 mm inside
   the plaster face, 1.98 cm off the old y max 24.0598, so the name is kept: SYNC.md 9, bbox within 2 cm); the UCX hulls are
   unchanged (collision never reached past the wall);
4. the hall builder's own QA + export recipe for a Nanite roof piece: add_uv1, qa_check (0 hard fails, the builder's
   waivers uv0_tile_range / uv_no_overlap), Scripts/pipeline export_fbx (static, no LODs: Nanite).
Run: blender -b --factory-startup --python Scripts/dojo/hall/fix_lower_front_clip.py -- [--no-export]
Out: Exports/DojoKit/Hall/SM_DKH_RoofLower_Front.fbx (the old one backed up to hall_armory/fix/start_backup first),
     WorkFiles/dojo/build/hall_armory/fix/json/fix_lower_front_clip.json
"""
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
for _p in (ROOT / "Scripts", ROOT / "Scripts" / "dojo", ROOT / "Scripts" / "dojo" / "roof",
           ROOT / "Scripts" / "dojo" / "materials", ROOT / "Scripts" / "dojo" / "hall"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
import build_hall as BH  # noqa: E402  (read-only: the builder's roof_pieces())
from kit_mesh import geo_to_object, add_uv1  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NAME = "SM_DKH_RoofLower_Front"
PIVOT = Vector((22.0, 29.0, 0.0))
CLIP_Y = 24.040          # world: the transom plaster's inner face is 24.045 (5 mm inside it; old y max 24.0598)
BAND_Z = (3.80, 4.10)
FBX = ROOT / "Exports" / "DojoKit" / "Hall" / f"{NAME}.fbx"
BACKUP = ROOT / "WorkFiles" / "dojo" / "build" / "hall_armory" / "fix" / "start_backup" / f"{NAME}.fbx"
REPORT = ROOT / "WorkFiles" / "dojo" / "build" / "hall_armory" / "fix" / "json" / "fix_lower_front_clip.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    t0 = time.time()
    assert_owner("DojoHall", "claude")
    rep = {"piece": NAME, "clip_y_world": CLIP_Y, "band_z": BAND_Z, "fbx_sha256_before": sha(FBX)}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    kit = bpy.data.collections.new("Kit")
    sc.collection.children.link(kit)
    roofs, _numbers = BH.roof_pieces()
    p = next(r for r in roofs if r.name == NAME)
    o, bad = geo_to_object(p, kit)
    rep["bad_faces"] = bad
    # ---- 2. the rebuild must reproduce the shipped mesh
    ref_coll = bpy.data.collections.new("Shipped")
    sc.collection.children.link(ref_coll)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    ship = [x for x in bpy.data.objects if x not in before and x.type == "MESH" and not x.name.startswith("UCX_")]
    ship_ucx = [x for x in bpy.data.objects if x not in before and x.name.startswith("UCX_")]
    assert len(ship) == 1, [x.name for x in ship]
    S = ship[0]
    Ms = S.matrix_world
    sv = [Ms @ v.co for v in S.data.vertices]
    ov = [o.matrix_world @ v.co for v in o.data.vertices]
    rep["verts"] = {"rebuilt": len(ov), "shipped": len(sv)}
    rep["ucx"] = {"rebuilt": len([c for c in o.children if c.name.startswith("UCX_")]), "shipped": len(ship_ucx)}

    def maxdev(a, b):
        kd = KDTree(len(b))
        for i, v in enumerate(b):
            kd.insert(v, i)
        kd.balance()
        return max(kd.find(v)[2] for v in a)

    dev = max(maxdev(ov, sv), maxdev(sv, ov))
    rep["rebuild_vs_shipped_max_dev_m"] = round(dev, 6)
    for x in ship + ship_ucx:
        bpy.data.objects.remove(x, do_unlink=True)
    if dev > 0.0005 or len(ov) != len(sv):
        rep["passed"] = False
        rep["why"] = "the builder no longer reproduces the shipped mesh: not exporting"
        REPORT.write_text(json.dumps(rep, indent=1), encoding="utf-8")
        print("FIX_CLIP FAILED", json.dumps(rep))
        return
    # ---- 3. clamp (the kit object sits at the origin in pivot space: world = PIVOT + local, no rotation)
    mw = Matrix.Translation(PIVOT) @ o.matrix_world
    inv = mw.inverted()
    moved, ymax_before = 0, -1e9
    for v in o.data.vertices:
        w = mw @ v.co
        ymax_before = max(ymax_before, w.y)
        if w.y > CLIP_Y and BAND_Z[0] <= w.z <= BAND_Z[1]:
            w.y = CLIP_Y
            v.co = inv @ w
            moved += 1
    o.data.update()
    ymax_after = max((mw @ v.co).y for v in o.data.vertices)
    rep["clamped_vertices"] = moved
    rep["y_max_world"] = {"before": round(ymax_before, 4), "after": round(ymax_after, 4),
                          "change_m": round(ymax_before - ymax_after, 4)}
    rep["bbox_change_within_2cm"] = (ymax_before - ymax_after) <= 0.02
    # left past the wall face anywhere in the wall band (X 13-31)?
    rep["left_past_inner_face"] = sum(1 for v in o.data.vertices
                                      if (mw @ v.co).y > 24.045 and 2.6 <= (mw @ v.co).z <= 5.0
                                      and 13.0 <= (mw @ v.co).x <= 31.0)
    # ---- 4. QA + export (the hall builder's recipe for a Nanite roof piece)
    o["nanite"] = True
    add_uv1(o)
    r = qa_check([o], require_uv1=True, texel_density=5.12, tolerance=0.25, overlap_method="operator")
    waive = {"uv0_tile_range", "uv_no_overlap"}          # build_hall.py's waivers for every hall piece
    fails = [c for c in r["checks"] if not c["passed"]]
    hard = [c for c in fails if c["name"] not in waive]
    rep["qa"] = {"hard_fails": [(c["name"], str(c["detail"])[:200]) for c in hard],
                 "waived": sorted({c["name"] for c in fails if c["name"] in waive}),
                 "tris": r["triangles"].get(NAME)}
    if hard:
        rep["passed"] = False
        rep["why"] = "qa_check hard fails"
    elif "--no-export" in ARGS:
        rep["passed"] = True
        rep["exported"] = False
    else:
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        if not BACKUP.exists():
            shutil.copy2(FBX, BACKUP)
        e = export_fbx(str(FBX), [o], kind="static", sidecar=False)
        rep["export_warnings"] = e.get("warnings")
        rep["fbx_sha256_after"] = sha(FBX)
        rep["fbx_bytes"] = FBX.stat().st_size
        rep["exported"] = True
        rep["passed"] = True
    rep["sec"] = round(time.time() - t0, 1)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print("FIX_CLIP", json.dumps(rep, default=str))


main()
