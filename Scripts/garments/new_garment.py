"""Start a garment: a new work file with the locked fitting body in it (headless Blender, never overwrites).

    blender -b --factory-startup --python Scripts/garments/new_garment.py -- \
        --name BlackHat --type rigid_head [--socket-bone thigh_l] [--base MH_PlayerDefault] [--out Assets/Garments/BlackHat.blend]

The file gets:

* ``FITBODY_<Base>`` - the locked body, head skin, hair proxy and the ``root`` armature (metahuman_base_skel),
  appended from ``References/Characters/<Base>/<Base>_FitBody.blend`` after checking its SHA-256 against
  ``base_lock.json``; unselectable. Model around it, never on it: ``garment_qa`` re-hashes it before export.
* ``GARMENT`` - the pieces that are skinned (everything, for fitted / rigid types),
* ``GARMENT_SIM`` - cloak only: the loose panels Chaos Cloth will simulate (one shared material),
* ``GARMENT_HELPERS`` - reference curves, cages, the anchor-bone marker; never exported.

Scene properties record the name, type, base, socket bone and the decimation targets that ``build_garment.py``
reads. A hard part (buckle, clasp, ring) gets the object property ``garment_hard = True``: never decimated, moved
rigidly by a refit. Types: ``cloak`` | ``fitted`` | ``rigid_head`` | ``rigid_socket`` (Scripts/garments/README.md).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
SCRIPTS = ROOT / "Scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import bpy  # noqa: E402

from pipeline import garment_helpers as gh  # noqa: E402
from pipeline import garment_qa as gq  # noqa: E402

ANCHOR = {"rigid_head": "head", "cloak": "spine_05"}


def create(name: str, garment_type: str, base: str, socket_bone: str = None, asset: str = None) -> dict:
    """Build the work-file scene in the current (empty) file; return the fitting body objects."""
    if garment_type not in gq.GARMENT_TYPES:
        raise ValueError(f"--type must be one of {gq.GARMENT_TYPES}")
    if garment_type == "rigid_socket" and not socket_bone:
        raise ValueError("rigid_socket needs --socket-bone (e.g. thigh_l, pelvis, spine_03)")
    units = bpy.context.scene.unit_settings
    units.system, units.scale_length, units.length_unit = "METRIC", 1.0, "METERS"
    fit = gh.append_fitbody(base)
    if socket_bone and fit["armature"].data.bones.get(socket_bone) is None:
        raise ValueError(f"{socket_bone!r} is not a bone of {base}")
    collections = gh.ensure_collections()
    if garment_type != "cloak":
        bpy.data.collections.remove(collections.pop(gh.SIM_COLLECTION))
    scene = bpy.context.scene
    sim_target, skin_target = gh.DEFAULT_TARGETS[garment_type]
    scene["garment_name"] = name
    scene["garment_asset"] = asset or name
    scene["garment_type"] = garment_type
    scene["garment_base"] = base
    scene["garment_socket_bone"] = socket_bone or ""
    scene["garment_sim_target_tris"] = sim_target
    scene["garment_skin_target_tris"] = skin_target
    scene["garment_export_name"] = "SK_" + name
    scene["garment_unique_uvs"] = False  # True for baked / hand-painted unique textures: UV0 overlap then fails
    anchor = socket_bone or ANCHOR.get(garment_type)
    if anchor:
        marker = bpy.data.objects.new(f"HELPER_Anchor_{anchor}", None)
        marker.empty_display_type = "ARROWS"
        marker.empty_display_size = 0.08
        marker.matrix_world = fit["armature"].matrix_world @ fit["armature"].data.bones[anchor].matrix_local
        collections[gh.HELPER_COLLECTION].objects.link(marker)
    return fit


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="new_garment.py")
    parser.add_argument("--name", required=True, help="garment name without prefix, e.g. BlackHat")
    parser.add_argument("--type", required=True, choices=gq.GARMENT_TYPES)
    parser.add_argument("--base", default=gq.DEFAULT_BASE)
    parser.add_argument("--socket-bone", default=None)
    parser.add_argument("--asset", default=None, help="lock name (default: --name)")
    parser.add_argument("--out", default=None, help="default Assets/Garments/<name>.blend")
    args = parser.parse_args(argv)
    out = Path(args.out) if args.out else ROOT / "Assets" / "Garments" / f"{args.name}.blend"
    if not out.is_absolute():
        out = ROOT / out
    if out.exists():
        print(f"NEW_GARMENT_REFUSED {out} exists (never overwritten)")
        return 1
    bpy.ops.wm.read_factory_settings(use_empty=True)
    create(args.name, args.type, args.base, args.socket_bone, args.asset)
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    print(f"NEW_GARMENT_OK {out} type={args.type} base={args.base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
