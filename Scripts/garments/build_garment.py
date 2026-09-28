"""Build, gate and export a garment work file (headless Blender; the work file is never saved).

    blender -b <work.blend> --factory-startup --python Scripts/garments/build_garment.py -- \
        --out Exports/Garments/<Name>/SK_<Name>.fbx [--agent claude] [--extra-loadout-tris N] \
        [--waive character_triangle_budget="reason"] [--gate-only]

Reads the scene properties ``new_garment.py`` / ``refit_garment.py`` wrote (type, base, socket bone, targets,
export name), then per type:

* all: drop SOLIDIFY / SUBSURF; decimate the GARMENT pieces to the skin target (``garment_hard`` pieces never);
* cloak: decimate GARMENT_SIM to the sim target, bake ``CLOTH_Pin`` to the ``PinMask`` colour, skin with
  ``skin_cloak`` (sim pieces rigid on the chest, the rest height-blended on the spine chain), give the sim pieces
  their ``*_Sim`` material copy (the cloth section);
* fitted: ``transfer_body_weights`` from the fitting body (8 influences);
* rigid_head / rigid_socket: every vertex on ``head`` / the socket bone;

joins everything into ``<export name>`` (the first sim piece first, so the cloth section is slot 0), parents it to
``root``, runs ``garment_qa`` and exports with ``export_fbx(kind="garment")`` only when every gate passes. Writes
``<name>.qa.json``, ``<name>.garment.json`` (the sidecar Unreal-side setup reads: type, skeleton, physics asset,
cloth section, waivers, hashes) and the unpacked textures into ``<out dir>/Textures``. Exit 1 when a gate fails.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
SCRIPTS = ROOT / "Scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import bpy  # noqa: E402

from pipeline import garment_helpers as gh  # noqa: E402
from pipeline import garment_qa as gq  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402


def build(settings: dict, fit: dict, report: dict) -> "bpy.types.Object":
    """Turn the GARMENT / GARMENT_SIM pieces into one skinned mesh; return it."""
    garment_type = settings["garment_type"]
    arm = fit["armature"]
    skinned, sim = gh.garment_pieces()
    if garment_type == "cloak" and not sim:
        raise ValueError("a cloak needs at least one piece in GARMENT_SIM (the cloth panels)")
    if garment_type != "cloak" and sim:
        raise ValueError(f"{garment_type} garments have no cloth section; empty GARMENT_SIM")
    pieces = skinned + sim
    if not pieces:
        raise ValueError("no meshes in GARMENT / GARMENT_SIM")
    report["pieces"] = {"skinned": [o.name for o in skinned], "sim": [o.name for o in sim]}
    report["kept_modifiers"] = gh.strip_build_modifiers(pieces)
    soft = [o for o in skinned if not o.get(gh.HARD_PROP)]
    report["decimate"] = {}
    if sim:
        report["decimate"]["sim"] = gh.decimate_group(sim, int(settings["garment_sim_target_tris"] or 0))
    report["decimate"]["skinned"] = gh.decimate_group(soft, int(settings["garment_skin_target_tris"] or 0))
    report["skinning"] = {}
    if garment_type == "cloak":
        report["pinned"] = {o.name: gh.bake_pin_mask(o) for o in pieces}
        for obj in pieces:
            report["skinning"][obj.name] = gh.skin_cloak(obj, arm, rigid=obj in sim)
        gh.make_sim_material(sim)
    elif garment_type == "fitted":
        for obj in pieces:
            report["skinning"][obj.name] = gh.transfer_body_weights(obj, [fit["body"], fit["head"]],
                                                                    gq.TYPE_RULES["fitted"]["max_influences"])
    else:
        bone = "head" if garment_type == "rigid_head" else settings["garment_socket_bone"]
        for obj in pieces:
            gh.skin_rigid(obj, bone)
            report["skinning"][obj.name] = bone
    first = sim[0] if sim else pieces[0]
    others = [o for o in soft if o is not first] + [o for o in sim if o is not first] + \
             [o for o in skinned if o.get(gh.HARD_PROP)]
    garment = gh.join(first, others, settings["garment_export_name"])
    report["ngons_triangulated"] = gh.triangulate_ngons(garment)
    gh.bind(garment, arm)
    if garment_type == "cloak":
        gh.set_active_pin_mask(garment)
    bpy.context.view_layer.update()
    report["joined"] = {"name": garment.name, "vertices": len(garment.data.vertices), "triangles": gh.tris(garment),
                        "slots": [m.name if m else None for m in garment.data.materials]}
    return garment


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="build_garment.py")
    parser.add_argument("--out", required=True, help="SK_<Name>.fbx")
    parser.add_argument("--agent", default="claude")
    parser.add_argument("--extra-loadout-tris", type=int, default=0)
    parser.add_argument("--waive", action="append", default=[])
    parser.add_argument("--gate-only", action="store_true", help="build and gate, do not export")
    args = parser.parse_args(argv)
    out = Path(args.out) if Path(args.out).is_absolute() else ROOT / args.out
    settings = gh.scene_settings()
    settings["garment_export_name"] = bpy.context.scene.get("garment_export_name") or "SK_" + settings["garment_name"]
    asset = bpy.context.scene.get("garment_asset") or settings["garment_name"]
    assert_owner(asset, args.agent)
    if out.stem != settings["garment_export_name"]:
        raise ValueError(f"--out must be named {settings['garment_export_name']}.fbx (the mesh name), got {out.name}")
    waivers = gq.parse_waivers(args.waive)
    report = {"work_file": bpy.data.filepath, "work_file_sha256": gq.file_sha256(Path(bpy.data.filepath)),
              "settings": settings, "started": datetime.now().astimezone().isoformat(timespec="seconds")}
    base = settings["garment_base"]
    lock = gq.load_base_lock(base)
    fit = {role: bpy.data.objects.get(name) for role, name in lock["objects"].items()}
    fit["armature"] = bpy.data.objects.get(lock["armature_object"])
    if fit["armature"] is None or fit["body"] is None:
        raise RuntimeError(f"the work file has no {lock['collection']}; start it with new_garment.py")
    garment = build(settings, fit, report)
    qa = gq.qa_garment([garment], settings["garment_type"], base=base,
                       socket_bone=settings["garment_socket_bone"] or None,
                       extra_loadout_tris=args.extra_loadout_tris, waive=waivers,
                       unique_uvs=bool(bpy.context.scene.get("garment_unique_uvs", False)))
    report["qa"] = qa
    out.parent.mkdir(parents=True, exist_ok=True)
    qa_path = out.with_suffix(".qa.json")
    status = "gated" if qa["passed"] else "failed_gates"
    if qa["passed"] and not args.gate_only:
        result = export_fbx(out, [garment], kind="garment")
        report["export"] = result
        # Post-condition: a garment FBX without its skeleton imports as a static-looking mesh with no error.
        data = out.read_bytes()
        limb_nodes = data.count(b"LimbNode")
        bones = len(fit["armature"].data.bones)
        if limb_nodes < bones or b"Cluster" not in data or "root" not in result["objects"]:
            raise RuntimeError(f"{out.name} lacks the skeleton or skin clusters ({limb_nodes} LimbNode for {bones} "
                               f"bones, objects {result['objects']})")
        report["fbx_skeleton_check"] = {"limb_nodes": limb_nodes, "bones": bones, "clusters": True}
        textures = gh.unpack_textures(out.parent / "Textures")
        sidecar = {
            "fbx": out.name, "fbx_sha256": gq.file_sha256(out), "garment_type": settings["garment_type"],
            "base": base, "skeleton": lock["unreal"]["skeleton"], "skeleton_hash": lock["skeleton_hash"],
            "physics_asset": lock["unreal"]["physics_asset"], "socket_bone": settings["garment_socket_bone"] or None,
            "cloth_section": next((m.name for m in garment.data.materials if m and m.name.endswith(gq.SIM_SUFFIX)), None),
            "pin_mask": gq.PIN_MASK if settings["garment_type"] == "cloak" else None,
            "material_slots": [m.name if m else None for m in garment.data.materials],
            "triangles": qa["metrics"].get("triangles"), "waived": qa["waived"],
            "textures": [Path(t).name for t in textures],
            "unreal_import": "FBX import onto the skeleton above (never create a new one): Import Normals, Convert "
                             "Scene ON, Force Front X OFF, no materials/textures/physics asset. Verified 2026-09-26 "
                             "through 5.8's default (Interchange) FBX path, which is what DemoGame_1 and CharacterLab "
                             "use (neither sets the legacy flag); expect the harmless 'invalid bind poses, rebind "
                             "using the time zero pose' warning (the pose is the rest pose). Then assign "
                             "the slots through MCP in the mesh's own slot order (Outfit_Pipeline traps 6/7) and "
                             "build the cloth on cloth_section from the PinMask red channel (trap 9)",
            "built": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        out.with_suffix(".garment.json").write_text(json.dumps(sidecar, indent=1), encoding="utf-8")
        report["sidecar"] = str(out.with_suffix(".garment.json"))
        status = "exported"
    report["status"] = status
    qa_path.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    failed = ", ".join(qa["failed"]) or "none"
    waived = ", ".join(w["name"] for w in qa["waived"]) or "none"
    print(f"BUILD_GARMENT_{status.upper()} {out} tris={report['joined']['triangles']} failed=[{failed}] "
          f"waived=[{waived}] report={qa_path}")
    return 0 if qa["passed"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("BUILD_GARMENT_ERROR")
        sys.exit(1)
