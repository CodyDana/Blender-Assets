"""Refit a garment sculpted on another body onto the locked base, producing a garment work file.

    blender -b "<COPY of the sculpt>.blend" --factory-startup --python Scripts/garments/refit_garment.py -- \
        --recipe Scripts/garments/recipes/BlackCloak.json --out WorkFiles/.../BlackCloak_MH_garment.blend [--agent claude]

For legacy garments only (the BlackCloak was sculpted around Manny); a new garment starts ON the base with
``new_garment.py``. The opened sculpt is never saved - the result is written with ``save_as_mainfile(copy=True)`` to
``--out`` (refused if it exists). The recipe (JSON) names the lock asset, the garment type, which pieces are cloth
(``sim_pieces``), the hard parts (``hard_prefix``), the collections to ignore, the decimation targets and the
source body FBX (Unreal export of the body the sculpt was made on, with its armature).

Steps: claim check (``lock.assert_owner``), source SHA-256 check, append the fitting body, sort the pieces into
GARMENT / GARMENT_SIM, report the fit on both bodies, ``garment_helpers.refit_warp`` (landmark TPS warp + clearance
pass with the hug rule; hard parts moved rigidly), report again, drop the source body, save. Writes
``<out>.refit.json`` beside the work file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
SCRIPTS = ROOT / "Scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import bpy  # noqa: E402

from pipeline import garment_helpers as gh  # noqa: E402
from pipeline import garment_qa as gq  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="refit_garment.py")
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--agent", default="claude")
    args = parser.parse_args(argv)
    recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8"))
    out = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    if out.exists():
        print(f"REFIT_REFUSED {out} exists (never overwritten)")
        return 1
    assert_owner(recipe["asset"], args.agent)
    source_path = Path(bpy.data.filepath)
    got = gq.file_sha256(source_path)
    if recipe.get("source_blend_sha256") and got != recipe["source_blend_sha256"]:
        raise RuntimeError(f"{source_path} sha256 {got} != recipe {recipe['source_blend_sha256']}")
    report = {"recipe": recipe, "source": str(source_path), "source_sha256": got}

    excluded = set(recipe.get("exclude_collections", []))
    pieces = [o for o in bpy.data.objects
              if o.type == "MESH" and not ({c.name for c in o.users_collection} & excluded)]
    sim_names = set(recipe.get("sim_pieces", []))
    missing = sim_names - {o.name for o in pieces}
    if missing:
        raise RuntimeError(f"sim_pieces not in the sculpt: {sorted(missing)}")
    hard_prefix = recipe.get("hard_prefix")
    for obj in pieces:
        if hard_prefix and obj.name.startswith(hard_prefix):
            obj[gh.HARD_PROP] = True

    # The base armature must own the name "root", and the source body's FBX brings a "root" of its own, so the
    # fitting body goes in first.
    fit = gh.append_fitbody(recipe["base"])
    target_skin = gh.SkinTree([fit["body"], fit["head"]])
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=recipe["source_body_fbx"], global_scale=1.0, automatic_bone_orientation=False)
    source_objects = [o for o in bpy.data.objects if o not in before]
    source_arm = next(o for o in source_objects if o.type == "ARMATURE")
    source_skin = gh.SkinTree([o for o in source_objects if o.type == "MESH"])
    report["source_body_fbx_sha256"] = gq.file_sha256(Path(recipe["source_body_fbx"]))
    report["crown"] = {"source": source_skin.top, "target": target_skin.top}
    report["before_on_source"] = gh.fit_report(pieces, source_skin)
    report["before_on_target"] = gh.fit_report(pieces, target_skin)
    report["refit"] = gh.refit_warp(pieces, sim_names, source_skin, target_skin, source_arm, fit["armature"],
                                    hug_max_bone=recipe.get("hug_max_bone", "neck_02"))
    report["after_on_target"] = gh.fit_report(pieces, target_skin)

    for obj in source_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    collections = gh.ensure_collections()
    for obj in pieces:
        gh.move_to(obj, collections[gh.SIM_COLLECTION if obj.name in sim_names else gh.GARMENT_COLLECTION])
    for collection in list(bpy.data.collections):
        if collection.name not in excluded and not collection.objects and not collection.children \
                and collection.name not in collections and collection.name != gq.fitbody_collection(recipe["base"]):
            bpy.data.collections.remove(collection)
    scene = bpy.context.scene
    scene["garment_name"] = recipe["name"]
    scene["garment_asset"] = recipe["asset"]
    scene["garment_type"] = recipe["type"]
    scene["garment_base"] = recipe["base"]
    scene["garment_socket_bone"] = recipe.get("socket_bone", "")
    scene["garment_sim_target_tris"] = recipe.get("sim_target_tris", gh.DEFAULT_TARGETS[recipe["type"]][0])
    scene["garment_skin_target_tris"] = recipe.get("skin_target_tris", gh.DEFAULT_TARGETS[recipe["type"]][1])
    scene["garment_export_name"] = recipe.get("export_name", "SK_" + recipe["name"])
    scene["garment_refit_from"] = str(source_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out), copy=True)
    report["out"] = str(out)
    Path(str(out) + ".refit.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(f"REFIT_OK {out} inside_before={report['before_on_target']['total_inside']} "
          f"inside_after={report['after_on_target']['total_inside']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("REFIT_FAILED")
        sys.exit(1)
