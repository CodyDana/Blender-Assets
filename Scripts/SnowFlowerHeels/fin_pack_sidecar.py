"""Finalise: write Exports/SnowFlowerHeels/SK_SnowFlowerHeels.skeletal.json, the sidecar the pack's material build
(Scripts/unreal/materials/np_skeletal.py) imports skeletal items from - derived from the garment sidecar, nothing typed
twice. In the pack's validation project the heels get their OWN copy of the 342-bone skeleton (that project has no
MetaHuman); in a game they are imported onto her metahuman_base_skel instead (README)."""
import json
from pathlib import Path

EXP = Path("C:/Users/Cody/Desktop/Blender_Projects/Exports/SnowFlowerHeels")
g = json.loads((EXP / "SK_SnowFlowerHeels.garment.json").read_text(encoding="utf-8"))
out = {
    "schema": "ninjapack.skeletal_prop/1",
    "fbx": g["fbx"], "asset": "SK_SnowFlowerHeels", "skeleton": "SK_SnowFlowerHeels_Skeleton", "root_bone": "root",
    "axes": {"blender": "armature space, right-handed, Z up (exported in cm)",
             "unreal": "component space, cm, left-handed (Blender y flipped), Z up"},
    "lod_files": g["lods"], "lod_screen_sizes": g["lod_screen_sizes"],
    "lod_note": "import LOD1/LOD2 with SkeletalMeshEditorSubsystem.import_lod; no bones removed",
    "import": {"use_t0_as_ref_pose": False, "import_morph_targets": False, "create_physics_asset": False,
               "normals": "import normals", "convert_scene": True, "force_front_x_axis": False},
    "animations": [], "sockets": [],
    "materials": g["material_slots"],
    "garment_sidecar": "SK_SnowFlowerHeels.garment.json",
    "note": "A garment on MH_PlayerFemale's metahuman_base_skel (342 bones incl. root). The pack project imports it onto "
            "its own skeleton copy only to carry the materials; in a game import it onto her skeleton (README.md).",
}
(EXP / "SK_SnowFlowerHeels.skeletal.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("PACK_SIDECAR_OK", out["lod_files"])
