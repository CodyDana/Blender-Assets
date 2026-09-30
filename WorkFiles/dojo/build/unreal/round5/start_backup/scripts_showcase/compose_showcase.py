"""DojoLab SHOWCASE (Blender side, headless): everything finished so far, in one layout, one blend and one bounds file.

Sources (read-only):
  WorkFiles/dojo/build/layout.json                      grey-box + KIT 1 (wall + gatehouse), markers, routes, cameras
  WorkFiles/dojo/build/ground/layout_ground.json        KIT 2 ground (replaces SM_DGB_Floor_Fight / _Path / _Yards)
  WorkFiles/dojo/build/props/<key>/layout_<key>.json    props: taiko, training, stone, modern (replace their stand-ins)
  Exports/DojoKit/**.fbx                                the exported deliverables themselves (what Unreal imports)

  WorkFiles/dojo/build/hall/layout_hall.json            (round 2) KITS 3 + 4 hall, replaces the grey-box hall + eave pads

Round 2 (2026-09-28): the hall kit is placed; the vending machine and roof ACs are placed UNSCALED (rebuilt to the
proven boxes) and their markers re-fitted to their UCX; Hall_Veranda / Landing_EavePad_* re-fitted to the hall kit; the
short lanterns come from layout_stone.json and sit on the floor under them (checked clear of the gate roof); every
material recipe is on the shared library's masters (M_DJ_Lib_Opaque / _Triplanar / _Emissive); blender_bounds.json
also carries each instance's all-LOD box (UE's non-Nanite render bounds). The round-1 rules below that no longer apply
(scaling the climb props, the stone layout's lantern proposal) are kept only as retired functions.

Rules applied here (task + house rules), every number computed and written to showcase/compose_report.json:
  - gate leaves at kit1.gate_leaf_placements.open (the player walks in); the rest of the compound stays grey-box
  - the grey-box's PROVEN climb numbers win: the vending machine is scaled to the grey-box box (0.9 x 0.8, top 1.75),
    the roof AC is scaled in Z about its front feet so its top is +5.10 (not +4.75); cisterns / crates are checked
    against their markers; the traversal markers are kept (weapon-rack markers re-fitted to the real rack's top rail)
  - ground pieces whose footprint is >= 95 % under the kit-1 gate paving are dropped (the paving is the gate floor),
    and the ground kit's gate kerb band family (its stand-in for the gate floor) with them
  - the grey-box pavilion loses its drum (the taiko replaces it): SM_DGB_Pavilion_NoDrum, exported through
    Scripts/pipeline to Exports/DojoKit/Showcase/
  - every prop stays its own instance; wires / rope / dressing get NoCollision; thin uprights block the pawn only
  - point lights at every emissive lamp (bulb / glass centre measured from the mesh)

Out:
  WorkFiles/dojo/build/showcase/layout_showcase.json    the one layout Unreal assembles (dj_sc_level.py)
  WorkFiles/dojo/build/showcase/blender_bounds.json     world AABB per instance + per-piece tris / slots / UCX / LODs
  WorkFiles/dojo/build/showcase/compose_report.json     fits, drops, deviations, counts
  Assets/Dojo/DojoShowcase.blend                        collections Kit (pieces + UCX) and Assembly (instances):
                                                        walk_check / climb_check / roof_walk_check run on it
Run: blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py [-- --no-export]
"""
import json
import math
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BUILD = ROOT / "WorkFiles" / "dojo" / "build"
SC = BUILD / "showcase"
EXP = ROOT / "Exports" / "DojoKit"
BLEND = ROOT / "Assets" / "Dojo" / "DojoShowcase.blend"
K_LUX = 100.0          # lux per Blender W/m2 (the armory's photometric factor): sun lux, candela and emissive radiance

L1 = json.loads((BUILD / "layout.json").read_text(encoding="utf-8"))
LG = json.loads((BUILD / "ground" / "layout_ground.json").read_text(encoding="utf-8"))
PROP_KEYS = ("taiko", "training", "stone", "modern")
LP = {k: json.loads((BUILD / "props" / k / f"layout_{k}.json").read_text(encoding="utf-8")) for k in PROP_KEYS}
LH = json.loads((BUILD / "hall" / "layout_hall.json").read_text(encoding="utf-8"))      # round 2: KITS 3 + 4 (the hall)
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
import dojo_materials as djm  # noqa: E402  (the shared library: set names, tiles, wear flags, emission strengths)
import dojo_tex_gen as djtg  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import look_r3  # noqa: E402  (round 3: look-pass instance values, close-up cameras, the dropped-lamp rules)
import round4  # noqa: E402  (round 4: outbuildings, corridors, shed, pavilion replace the last grey-box buildings)

KITS = {   # kit -> FBX folder, texture folder, Unreal content root
    "greybox": (EXP, None, "/Game/DojoKit/Greybox"),
    "showcase": (EXP / "Showcase", None, "/Game/DojoKit/Showcase"),
    "library": (None, EXP / "Materials" / "Textures", "/Game/DojoKit/Materials"),     # the shared library (T_DJ_*)
    "hall": (EXP / "Hall", None, "/Game/DojoKit/Hall"),                               # library materials only
    "kit1": (EXP / "Kit1", EXP / "Kit1" / "Textures", "/Game/DojoKit/Kit1"),
    "ground": (EXP / "Ground", EXP / "Ground" / "Textures", "/Game/DojoKit/Ground"),
    "taiko": (EXP / "Props" / "taiko", EXP / "Props" / "taiko" / "Textures", "/Game/DojoKit/Props/Taiko"),
    "training": (EXP / "Props" / "training", EXP / "Props" / "training" / "Textures", "/Game/DojoKit/Props/Training"),
    "stone": (EXP / "Props" / "stone", EXP / "Props" / "stone" / "Textures", "/Game/DojoKit/Props/Stone"),
    "modern": (EXP / "Props" / "modern", EXP / "Props" / "modern" / "Textures", "/Game/DojoKit/Props/Modern"),
}
# grey-box stand-ins the kits replace (kit 1's own list is in layout.json kit1.replaced_greybox and already applied)
REPLACED_GB = {
    "SM_DGB_Floor_Fight": "ground", "SM_DGB_Floor_Path": "ground", "SM_DGB_Floor_Yards": "ground",
    "SM_DGB_Cistern": "stone", "SM_DGB_Crate": "stone", "SM_DGB_Well": "stone", "SM_DGB_StoneLantern": "stone",
    "SM_DGB_Vending": "modern", "SM_DGB_ACUnit": "modern",
    "SM_DGB_WeaponRack": "training", "SM_DGB_TrainingPost": "training", "SM_DGB_Dummy": "training",
}
REPLACED_GB.update({n: "hall" for n in LH["replaces_greybox"]})   # body, veranda, step band, roofs, eave pads
KITS.update(round4.KITS)                  # round 4 (2026-09-29): the remaining buildings
LR4 = round4.LAYOUTS
REPLACED_GB.update(round4.replaced_greybox())   # storehouse, residence, corridors, shed, pavilion (+ NoDrum, pad)
R4_KITS = tuple(round4.KITS)
PAVILION_NODRUM = "SM_DGB_Pavilion_NoDrum"
COLLISION_EXTRA = {
    "propblock": {"pawn": "block", "camera": "ignore", "visibility": "block",
                  "note": "blocking prop, unwalkable (the taiko drum): camera ignore so it never yanks the camera"},
    "lowcover": {"pawn": "block", "camera": "block", "visibility": "block", "note": "low cover <= 1.25 m (R8): the well"},
    "nocollision": {"pawn": "ignore", "camera": "ignore", "visibility": "ignore", "no_collision": True,
                    "note": "wires, rope, hanging bucket, drum sticks, ground dressing: NoCollision in Unreal"},
}
TAIKO_CLASS = {"SM_DKP_Taiko_Drum": "propblock", "SM_DKP_Taiko_Stand": "thin", "SM_DKP_Taiko_Stick": "nocollision"}
STONE_CLASS = {"thin_upright": "thin", "climb_prop": "climbprop", "low_cover": "lowcover", "prop_small": "nocollision",
               "no_collision": "nocollision"}
STONE_PIECE_CLASS = {"SM_DKP_Stone_Cistern": "climbprop", "SM_DKP_Stone_Crate": "climbprop",
                     "SM_DKP_Stone_CrateHalf": "climbprop", "SM_DKP_Stone_LanternShort": "thin",
                     "SM_DKP_Stone_LanternTall": "thin", "SM_DKP_Stone_Well": "lowcover",
                     "SM_DKP_Stone_WellCover": "lowcover", "SM_DKP_Stone_WellFrame": "thin",
                     "SM_DKP_Stone_WellFrameGable": "thin", "SM_DKP_Stone_WellPulley": "thin",
                     "SM_DKP_Stone_WellBucket": "nocollision", "SM_DKP_Stone_WellRope": "nocollision"}
MODERN_CLASS = {"climbprop": "climbprop", "thin": "thin", "wire": "nocollision"}
NANITE_MIN_TRIS = 2000     # task: Nanite ON for pieces over ~2k tris (props); kit 1 keeps its own per-piece flags
# lamps: which emissive slot marks the light centre, and its Blender power (W) -> candela = K P / (4 pi)
# (round 2: kit 1's lamp and the stone lanterns glow with the library's M_DJ_GlassAmber now)
LAMP_LIGHTS = {"SM_DK_Gate_Lamp": ("M_DJ_GlassAmber", 45.0, 2400, 9.0),            # render_kit1.py lamp_lights 45 W
               "SM_DKP_Stone_LanternTall": ("M_DJ_GlassAmber", 20.0, 2300, 7.0),
               "SM_DKP_Stone_LanternShort": ("M_DJ_GlassAmber", 15.0, 2300, 6.0),
               "SM_DKP_Modern_WallLamp": ("M_DKP_Modern_BulbLit", 30.0, 2600, 8.0),
               "SM_DKP_Modern_StreetLamp_A": ("M_DKP_Modern_BulbLit", 35.0, 2600, 9.0),
               "SM_DKP_Modern_StreetLamp_B": ("M_DKP_Modern_BulbLit", 30.0, 2600, 8.0)}
REPORT = {"notes": [], "deviations": [], "drops": {}, "fits": {}, "warnings": []}


def strip(name):
    return re.sub(r"\.\d{3}$", "", name)


def world_bbox(obj, mw=None):
    mw = obj.matrix_world if mw is None else mw
    pts = [mw @ Vector(c) for c in obj.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def union(boxes):
    return ([min(b[0][i] for b in boxes) for i in range(3)], [max(b[1][i] for b in boxes) for i in range(3)])


def rnd(v, n=4):
    return [round(float(x), n) for x in v]


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


# ------------------------------------------------------------------------------------------------ import
KIT_COLL = ASM_COLL = None


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    global KIT_COLL, ASM_COLL
    KIT_COLL = bpy.data.collections.new("Kit")
    ASM_COLL = bpy.data.collections.new("Assembly")
    bpy.context.scene.collection.children.link(KIT_COLL)
    bpy.context.scene.collection.children.link(ASM_COLL)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0


def import_piece(piece, fbx):
    """Import one exported FBX; keep LOD0 as `piece` with its UCX children in Kit. Returns the piece meta."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH" and not o.name.startswith("UCX_")]
    lods = sorted([o for o in meshes if re.search(r"_LOD\d+$", strip(o.name))], key=lambda o: o.name)
    main = next((o for o in meshes if strip(o.name) == piece), None)
    if lods:
        main = next(o for o in lods if strip(o.name).endswith("_LOD0"))
    if main is None:
        raise RuntimeError(f"{fbx}: no mesh named {piece}")
    lod_boxes = [world_bbox(o) for o in (lods or [main])]
    lod_tris = [tri_count(o) for o in (lods or [main])]
    ucx = [o for o in new if o.name.startswith("UCX_")]
    for o in ucx:
        if o.parent is not main:
            mw = o.matrix_world.copy()
            o.parent = main
            o.matrix_world = mw
    for o in new:
        for c in list(o.users_collection):
            c.objects.unlink(o)
    keep = {main} | set(ucx)
    for o in new:
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    if main.parent is not None:
        mw = main.matrix_world.copy()
        main.parent = None
        main.matrix_world = mw
    main.name = piece
    main.data.name = piece
    KIT_COLL.objects.link(main)
    for o in ucx:
        KIT_COLL.objects.link(o)
    if any(abs(v) > 1e-6 for v in main.matrix_world.translation) or \
            any(abs(main.matrix_world[i][j] - (1.0 if i == j else 0.0)) > 1e-6 for i in range(3) for j in range(3)):
        REPORT["warnings"].append(f"{piece}: imported with a non-identity transform {list(map(list, main.matrix_world))}")
    ub = union([world_bbox(o) for o in ucx]) if ucx else None
    return {"slots": [strip(s.material.name) if s.material else None for s in main.material_slots],
            "tris": tri_count(main), "lod_tris": lod_tris, "lods": len(lod_tris),
            "ucx": sorted(o.name for o in ucx), "n_ucx": len(ucx),
            "vcol": [a.name for a in main.data.color_attributes],
            "bbox_lod0": [rnd(lod_boxes[0][0], 5), rnd(lod_boxes[0][1], 5)],
            "bbox_all_lods": [rnd(union(lod_boxes)[0], 5), rnd(union(lod_boxes)[1], 5)],
            "ucx_bbox": [rnd(ub[0], 5), rnd(ub[1], 5)] if ub else None}


def make_nodrum(src):
    """SM_DGB_Pavilion without its drum: the drum faces (slot M_DGB_Drum) and the drum hull go; exported through the
    pipeline (qa_check 0 hard fails; the flat-colour grey-box waives uv0_tile_range / uv_no_overlap as before)."""
    ob = src.copy()
    ob.data = src.data.copy()
    KIT_COLL.objects.link(ob)
    ob.name = ob.data.name = PAVILION_NODRUM
    slots = [strip(s.material.name) for s in ob.material_slots]
    di = slots.index("M_DGB_Drum")
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    drum = [f for f in bm.faces if f.material_index == di]
    dz = [v.co for f in drum for v in f.verts]
    dmin = Vector([min(p[i] for p in dz) for i in range(3)])
    dmax = Vector([max(p[i] for p in dz) for i in range(3)])
    bmesh.ops.delete(bm, geom=drum, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.materials.pop(index=di)
    for k, m in enumerate(ob.data.materials):   # FBX re-import suffixes duplicate names (M_DGB_Stone.001): export the
        base = strip(m.name)                     # exact slot names the grey-box instances carry
        exact = bpy.data.materials.get(base)
        if exact is None:
            m.name = base
        else:
            ob.data.materials[k] = exact
    hulls = []
    dropped = None
    for h in src.children:
        if not h.name.startswith("UCX_"):
            continue
        hmin, hmax = world_bbox(h)
        if max(abs(a - b) for a, b in zip(list(hmin) + list(hmax), list(dmin) + list(dmax))) < 0.01:
            dropped = h.name
            continue
        hc = h.copy()
        hc.data = h.data.copy()
        KIT_COLL.objects.link(hc)
        hc.parent = ob
        hc.matrix_world = h.matrix_world.copy()
        hulls.append(hc)
    if dropped is None:
        raise RuntimeError("no UCX hull matches the grey-box drum")
    for i, h in enumerate(hulls):
        h.name = h.data.name = f"UCX_{PAVILION_NODRUM}_{i:02d}"
    REPORT["notes"].append(f"{PAVILION_NODRUM}: drum faces and hull {dropped} removed "
                           f"(drum box {rnd(dmin, 3)} - {rnd(dmax, 3)}), {len(hulls)} hulls kept")
    r = qa_check([ob], require_uv1=True)
    waive = {"uv0_tile_range", "uv_no_overlap"}
    hard = [c for c in r["checks"] if not c["passed"] and c["name"] not in waive]
    REPORT["nodrum_qa"] = {"hard_fails": hard, "tris": r["triangles"].get(ob.name)}
    if hard:
        raise RuntimeError(f"{PAVILION_NODRUM} QA hard fails: {hard}")
    out = KITS["showcase"][0] / f"{PAVILION_NODRUM}.fbx"
    if "--no-export" not in ARGS:
        out.parent.mkdir(parents=True, exist_ok=True)
        e = export_fbx(str(out), [ob], kind="static", sidecar=False)
        REPORT["nodrum_export"] = {"file": str(out), "objects": e["objects"], "warnings": e["warnings"]}
    return ob


# ------------------------------------------------------------------------------------------------ pieces
def piece_table():
    """piece -> {kit, fbx, sidecar, class, folder, nanite, note}"""
    P = {}
    for name, p in L1["pieces"].items():
        if name.startswith("SM_DGB_"):
            if name in REPLACED_GB:
                continue
            kit = "greybox"
        else:
            kit = "kit1"
        P[name] = {"kit": kit, "class": p["class"], "folder": p.get("folder", "Misc"), "note": p.get("note", ""),
                   "nanite": bool(p.get("nanite", False))}
    if PAVILION_NODRUM not in REPLACED_GB:   # round 4: the pavilion kit replaces the drum-less grey-box pavilion
        P.pop("SM_DGB_Pavilion")
        P[PAVILION_NODRUM] = {"kit": "showcase", "class": "building", "folder": "Yard", "nanite": False,
                              "note": "grey-box drum pavilion without its drum (the taiko kit replaces it)"}
    for name in LG["pieces"]:
        meta = LG["piece_meta"].get(name, {})
        P[name] = {"kit": "ground", "class": "ground" if meta.get("collision", True) else "nocollision",
                   "folder": "Ground/" + meta.get("family", "misc").capitalize(), "nanite": False,
                   "note": meta.get("family", "")}
    for name, p in LP["taiko"]["pieces"].items():
        P[name] = {"kit": "taiko", "class": TAIKO_CLASS[name], "folder": "Props/Taiko", "note": p.get("pivot", "")}
    for name, p in LP["training"]["pieces"].items():
        P[name] = {"kit": "training", "class": "thin", "folder": "Props/Training", "note": p.get("traversal", "")}
    for name in LP["stone"]["pieces"]:
        P[name] = {"kit": "stone", "class": STONE_PIECE_CLASS[name], "folder": "Props/Stone", "note": ""}
    for name, p in LP["modern"]["pieces"].items():
        P[name] = {"kit": "modern", "class": MODERN_CLASS[p["class"]], "folder": "Props/Modern", "note": p.get("note", "")[:160]}
    for name, p in LH["pieces"].items():   # round 2: the hall kit (its own Nanite flags: pieces of 2k tris or more)
        P[name] = {"kit": "hall", "class": p["class"], "folder": p["folder"], "nanite": bool(p["nanite"]),
                   "note": p.get("note", "")[:160]}
    for kit, LK in LR4.items():   # round 4: each kit's own Nanite flags (pieces of about 2k tris or more)
        for name, p in LK["pieces"].items():
            P[name] = {"kit": kit, "class": p["class"], "folder": p["folder"], "nanite": bool(p["nanite"]),
                       "note": p.get("note", "")[:160]}
    for name, p in P.items():
        d = KITS[p["kit"]][0]
        p["fbx"] = str(d / f"{name}.fbx")
        sc = d / f"{name}.sockets.json"
        p["sidecar"] = str(sc) if sc.exists() else None
        p["ue_dir"] = KITS[p["kit"]][2] + "/Meshes"
    return P


# ------------------------------------------------------------------------------------------------ instances
def inst(piece, loc, rot_z=0.0, kit="", folder=None, cls=None, scale=(1.0, 1.0, 1.0), rot_xyz=None, source="", note=""):
    return {"piece": piece, "loc": [float(v) for v in loc],
            "rot_xyz_deg": [float(v) for v in (rot_xyz if rot_xyz is not None else (0.0, 0.0, rot_z))],
            "rot_z": float(rot_xyz[2] if rot_xyz is not None else rot_z), "scale": [float(v) for v in scale],
            "folder": folder, "collision_class": cls, "kit": kit, "source": source, "note": note}


def base_instances():
    out = []
    opened = {it["piece"]: it for it in L1["kit1"]["gate_leaf_placements"]["open"]}
    for n, i in enumerate(L1["instances"]):
        piece = i["piece"]
        if piece in REPLACED_GB:
            continue
        if piece == "SM_DGB_Pavilion":
            out.append(inst(PAVILION_NODRUM, i["loc"], i["rot_z"], "showcase", i["folder"], "building",
                            source=f"layout.json #{n} SM_DGB_Pavilion (drum removed)"))
            continue
        loc, rz, note = i["loc"], i["rot_z"], ""
        if piece in opened:
            loc, rz, note = opened[piece]["loc"], opened[piece]["rot_z"], "gate leaf OPEN (kit1.gate_leaf_placements.open)"
        out.append(inst(piece, loc, rz, "greybox" if piece.startswith("SM_DGB_") else "kit1", i["folder"],
                        i["collision_class"], source=f"layout.json #{n}", note=note))
    return out


def ground_instances(P):
    return [inst(i["piece"], i["loc"], i["rot_z"], "ground", "Ground/" + LG["piece_meta"].get(i["piece"], {}).get(
        "family", "misc").capitalize(), P[i["piece"]]["class"], source=f"layout_ground.json #{n}",
        note="") | {"bbox_layout": i.get("bbox_min_max")} for n, i in enumerate(LG["instances"])]


def prop_instances():
    out = []
    for n, i in enumerate(LP["taiko"]["instances"]):
        out.append(inst(i["piece"], i["loc"], kit="taiko", folder="Props/Taiko", cls=TAIKO_CLASS[i["piece"]],
                        rot_xyz=i["rot_xyz_deg"], source=f"layout_taiko.json #{n}"))
    for n, i in enumerate(LP["training"]["instances"]):
        out.append(inst(i["piece"], i["loc"], i["rot_z"], "training", "Props/Training", "thin",
                        source=f"layout_training.json #{n}", note=i.get("source", "")[:160]))
    for n, i in enumerate(LP["stone"]["instances"]):
        # round 2: the stone layout itself places the short lanterns (user 2026-10-02: flanking the path just inside
        # the gate, in the courtyard, not under the gate roof); their z is set on whatever floor is under them below
        out.append(inst(i["piece"], i["loc"], i["rot_z"], "stone", "Props/Stone", STONE_CLASS[i["collision_class"]],
                        source=f"layout_stone.json #{n}", note=i.get("source", "")[:160]))
    for n, i in enumerate(LP["modern"]["instances"]):
        out.append(inst(i["piece"], i["loc"], i["rot_z"], "modern", "Props/Modern",
                        MODERN_CLASS[LP["modern"]["pieces"][i["piece"]]["class"]], scale=i.get("scale", (1, 1, 1)),
                        source=f"layout_modern.json #{n}", note=i.get("note", "")[:160]))
    return out


def hall_instances():
    """round 2: the hall kit (layout_hall.json, grey-box world frame) in place of the grey-box hall pieces."""
    return [inst(i["piece"], i["loc"], i["rot_z"], "hall", i["folder"], i["collision_class"],
                 source=f"layout_hall.json #{n}") for n, i in enumerate(LH["instances"])]


def round4_instances():
    """round 4: the four kits' own layouts (grey-box world frame) in place of the grey-box buildings."""
    out = []
    for kit, LK in LR4.items():
        rel = round4.LAYOUT_FILES[kit].relative_to(BUILD).as_posix()
        for n, i in enumerate(LK["instances"]):
            out.append(inst(i["piece"], i["loc"], i["rot_z"], kit, i["folder"], i["collision_class"],
                            source=f"{rel} #{n}"))
    return out


def apply_prop_moves(props):
    """round 4: the outbuildings track's measured proposals (layout_outbuildings_checks.json)."""
    done = []
    for mv in round4.prop_moves():
        hits = [i for i in props if i["piece"] == mv["piece"]
                and max(abs(a - b) for a, b in zip(i["loc"], mv["from"])) < 1e-3]
        if len(hits) != 1:
            raise RuntimeError(f"prop move {mv['piece']} from {mv['from']}: {len(hits)} matches")
        i = hits[0]
        i["loc"] = [float(v) for v in mv["to"]]
        i["rot_xyz_deg"] = [0.0, 0.0, float(mv["rot_z"])]
        i["rot_z"] = float(mv["rot_z"])
        i["note"] = (f"round 4 move from {mv['from']}: {mv['why']}; " + i["note"])[:200]
        done.append(mv)
    return done


def fit_round4_markers(markers, instances, kit_objs):
    """round 4: route 7's shed band and pavilion pad and the plinth marker re-fitted to the kits' own UCX hulls (the
    tracks built them to the grey-box boxes: the delta is measured and reported, expected 0)."""
    rows = {}
    for mname, (piece, pick, _sides) in round4.MARKER_FITS.items():
        m = next(m for m in markers if m["name"] == mname)
        cands = [i for i in instances if i["piece"] == piece]
        if len(cands) != 1:
            raise RuntimeError(f"marker {mname}: {len(cands)} instances of {piece}")
        mw = matrix_of(cands[0])
        hulls = [world_bbox(h, mw @ h.matrix_local) for h in kit_objs[piece].children if h.name.startswith("UCX_")]
        if "min_y" in pick:
            hulls = [b for b in hulls if b[0][1] >= pick["min_y"] - 1e-6]
        hulls.sort(key=lambda b: (round(abs(b[1][2] - pick["top"]), 3),
                                  -(b[1][0] - b[0][0]) * (b[1][1] - b[0][1]) if pick.get("largest") else 0.0))
        b = hulls[0]
        box = [b[0][0], b[1][0], b[0][1], b[1][1], m["box"][4], b[1][2]]
        rows[mname] = {"piece": piece, "grey_box": list(m["box"]), "refit": rnd(box, 4),
                       "max_delta_m": round(max(abs(p - q) for p, q in zip(box, m["box"])), 4)}
        m["box"] = rnd(box, 4)
        m["note"] = (f"round 4: {piece} UCX (top +{box[5]:.3f}); " + m.get("note", ""))[:300]
    return rows


def matrix_of(i):
    return (Matrix.Translation(Vector(i["loc"])) @ Euler([math.radians(a) for a in i["rot_xyz_deg"]], "XYZ").to_matrix().to_4x4()
            @ Matrix.Diagonal(Vector(i["scale"] + [1.0])))


def floor_at(x, y, instances, kit_objs):
    """Highest render-mesh surface straight down at (x, y) among the given instances: (z, 'piece__n') or (None, None)."""
    best, who = None, None
    for n, i in enumerate(instances):
        ob = kit_objs[i["piece"]]
        mw = matrix_of(i)
        lo, hi = world_bbox(ob, mw)
        if not (lo[0] - 1e-4 <= x <= hi[0] + 1e-4 and lo[1] - 1e-4 <= y <= hi[1] + 1e-4):
            continue
        inv = mw.inverted()
        o = inv @ Vector((x, y, hi[2] + 1.0))
        d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
        ok, loc, _nrm, _idx = ob.ray_cast(o, d)
        if ok:
            z = (mw @ loc).z
            if best is None or z > best:
                best, who = z, i["piece"]
    return best, who


def ucx_world_box(piece_obj, mw):
    boxes = []
    for h in piece_obj.children:
        if h.name.startswith("UCX_"):
            boxes.append(world_bbox(h, mw @ h.matrix_local))
    return union(boxes) if boxes else None


# ------------------------------------------------------------------------------------------------ fits
def marker(name):
    return next(m for m in L1["traversal_markers"] if m["name"] == name)


def fit_climb_props(instances, meta):
    """Round 2: the modern kit rebuilt both climb props to the grey-box's proven boxes (the vending machine at its true
    0.80 m depth, the roof AC with its casing top at +5.10), so NOTHING is scaled any more: this only measures each
    placed prop's UCX box against its grey-box marker (the markers are then re-fitted to the props, below)."""
    fits = {}
    for i in instances:
        if i["piece"] not in ("SM_DKP_Modern_VendingMachine", "SM_DKP_Modern_ACUnit_Roof"):
            continue
        if any(abs(s - 1.0) > 1e-9 for s in i["scale"]):
            raise RuntimeError(f"{i['piece']} at {i['loc']}: scale {i['scale']} (round 2 places the rebuilt props unscaled)")
    return fits


def fit_climb_props_round1(instances, meta):
    """(round 1, retired 2026-09-28) Place / scale the climb props to the grey-box's proven boxes."""
    fits = {}
    # vending machine -> Vending marker box (0.9 x 0.8 x 1.75): rot 180 (front faces north), scale to the box
    mk = marker("Vending")["box"]
    for i in instances:
        if i["piece"] != "SM_DKP_Modern_VendingMachine":
            continue
        (lx0, ly0, lz0), (lx1, ly1, lz1) = meta[i["piece"]]["ucx_bbox"]
        sx, sy, sz = (mk[1] - mk[0]) / (lx1 - lx0), (mk[3] - mk[2]) / (ly1 - ly0), (mk[5] - mk[4]) / (lz1 - lz0)
        before = {"loc": list(i["loc"]), "scale": list(i["scale"])}
        i["scale"] = [sx, sy, sz]
        i["loc"] = [mk[0] + sx * lx1, mk[2] + sy * ly1, mk[4] - sz * lz0]   # rot 180: world = loc - s * local
        i["note"] = ("scaled to the grey-box vending box (route 8 proven at 80 cm deep): " + i["note"])[:200]
        fits["vending"] = {"ucx_local": meta[i["piece"]]["ucx_bbox"], "marker": mk, "scale": rnd(i["scale"], 5),
                           "loc": rnd(i["loc"], 5), "layout_modern": before,
                           "depth_m_before": round(ly1 - ly0, 4), "width_m_before": round(lx1 - lx0, 4)}
    # roof AC -> top +5.10 (grey-box ACUnit markers): Z scale about the front feet (the pivot, on the lower roof)
    for side, mname in (("W", "ACUnit_W"), ("E", "ACUnit_E")):
        mk = marker(mname)["box"]
        cands = [i for i in instances if i["piece"] == "SM_DKP_Modern_ACUnit_Roof"
                 and mk[0] - 0.01 <= i["loc"][0] <= mk[1] + 0.01]
        i = cands[0]
        top_local = meta[i["piece"]]["ucx_bbox"][1][2]
        sz = (mk[5] - i["loc"][2]) / top_local
        i["scale"] = [1.0, 1.0, sz]
        i["note"] = f"Z scale {sz:.4f} about the front feet: top +{mk[5]:.2f} (grey-box route 5), not the spec's +4.75"
        fits[f"ac_{side}"] = {"marker": mk, "pivot_z": i["loc"][2], "ucx_top_local": top_local, "scale_z": round(sz, 5),
                              "top_before": round(i["loc"][2] + top_local, 4)}
    return fits


def check_markers(instances, kit_objs):
    """Every climb-prop marker against the UCX box of the prop placed there (after the fits)."""
    rows = {}
    for m in L1["traversal_markers"]:
        if not m["name"].startswith(("Cistern", "ACUnit", "Crate", "Vending", "WeaponRack")):
            continue
        x0, x1, y0, y1, z0, z1 = m["box"]
        best = None
        for n, i in enumerate(instances):
            if not i["piece"].startswith("SM_DKP_") or i["collision_class"] in ("nocollision",):
                continue
            b = ucx_world_box(kit_objs[i["piece"]], matrix_of(i))
            if b is None:
                continue
            ox = min(x1, b[1][0]) - max(x0, b[0][0])
            oy = min(y1, b[1][1]) - max(y0, b[0][1])
            if ox > 0.05 and oy > 0.05 and b[1][2] > z0 + 0.3:
                d = max(abs(x0 - b[0][0]), abs(x1 - b[1][0]), abs(y0 - b[0][1]), abs(y1 - b[1][1]), abs(z1 - b[1][2]))
                if best is None or d < best[0]:
                    best = (d, n, i["piece"], b)
        if best:
            d, n, piece, b = best
            rows[m["name"]] = {"prop": piece, "instance": n, "marker": m["box"], "ucx_box": rnd(b[0] + b[1], 4),
                               "max_edge_or_top_delta_m": round(d, 4)}
    return rows


def ground_vs_paving(ground, kit_objs, base):
    """Fraction of each ground instance's footprint under the kit-1 gate paving (rays straight down, 5 cm grid)."""
    pav = next(i for i in base if i["piece"] == "SM_DK_Gate_Paving")
    ob = kit_objs["SM_DK_Gate_Paving"]
    mw = matrix_of(pav)
    verts = [mw @ v.co for v in ob.data.vertices]
    bvh = BVHTree.FromPolygons(verts, [list(p.vertices) for p in ob.data.polygons])
    keep, dropped = [], []
    for i in ground:
        x0, y0, _z0, x1, y1, _z1 = i["bbox_layout"]
        nx, ny = max(2, int((x1 - x0) / 0.05)), max(2, int((y1 - y0) / 0.05))
        hit = tot = 0
        for a in range(nx):
            for b in range(ny):
                p = Vector((x0 + (a + 0.5) * (x1 - x0) / nx, y0 + (b + 0.5) * (y1 - y0) / ny, 3.0))
                tot += 1
                if bvh.ray_cast(p, Vector((0, 0, -1)), 5.0)[0] is not None:
                    hit += 1
        f = hit / tot
        i["paving_cover"] = round(f, 4)
        # the ground kit's gate kerb band family (Kerb50 blocks, their sloped ends and the joint fill) stood in for the
        # gate floor the kit-1 paving now is: the whole family goes, ends included
        band = i["piece"].startswith(("SM_DKG_Kerb50", "SM_DKG_KerbMortar")) and f > 0.0
        # drop only what the paving hides completely (>= 95 %): a partly covered slab / bed / panel stays under the
        # paving's edge (the paving is 1-8 cm higher), so no hole opens where the grey-box floor used to be
        (dropped if f >= 0.95 or band else keep).append(i)
    REPORT["drops"]["ground_under_gate_paving"] = [{"piece": i["piece"], "loc": i["loc"], "cover": i["paving_cover"]}
                                                   for i in dropped]
    REPORT["partial_ground_under_paving"] = [{"piece": i["piece"], "loc": i["loc"], "cover": i["paving_cover"]}
                                             for i in keep if i["paving_cover"] > 0]
    return keep, bvh


# ------------------------------------------------------------------------------------------------ materials
def hexcol(h):
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return [round(lin(int(h[i:i + 2], 16) / 255.0), 5) for i in (1, 3, 5)]


def tset(kit, stem):
    d = KITS[kit][1]
    return {"Base Colour Map": f"{stem}_BC", "ORM Map": f"{stem}_ORM", "Normal Map": f"{stem}_N"}, \
        {f"{stem}_{s}": str(d / f"{stem}_{s}.png") for s in ("BC", "ORM", "N")}


def _kit1_const(name):
    """A constant of Scripts/dojo/build_kit1.py (FS_FLAT, FS_MEAN ...), read from its source: one source of truth."""
    src = (ROOT / "Scripts" / "dojo" / "build_kit1.py").read_text(encoding="utf-8")
    m = re.search(rf"^{name}\s*=\s*([^#\n]+)", src, re.M)
    if m is None:
        raise RuntimeError(f"build_kit1.py has no {name}")
    return eval(m.group(1), {})   # a number or a tuple literal


def material_recipes(used_slots, slot_kits):
    """Round 2 (2026-09-28): slot name -> Unreal instance recipe on the SHARED LIBRARY's masters
    (Scripts/dojo/materials/README.md 'Unreal 5.8 recipe'):
      M_DJ_Lib_Opaque     UV0: BC x Tint (lerp to MeanColour by FlattenToMean), moss lerp by VertexColor.A (UseMoss),
                          the library wear maths on the 'Wear' vertex colour (UseWear, WearMask at UV0 x TileM),
                          per-actor tone / hue (UseInstanceVar); roughness ORM.g x RoughMult; N flattened by
                          NormalStrength
      M_DJ_Lib_Triplanar  the same on world-aligned projection (TextureSize = tile_m x 100 cm): round stone, the
                          earthen wall plaster and kit 1's earth core
      M_DJ_Lib_Emissive   BaseColor = BC x BaseMult, Emissive = BC x EmissiveIntensity x EmissiveTint
    plus the ground kit's own masters (sand / gravel / bed blend / dressing), the masked grille and the flat colours.
    Emissive intensity = Blender strength x K_LUX (the armory's photometric factor). slot_kits: slot -> kits using it."""
    R, TEX = {}, {}
    LIB = KITS["library"]

    def add(name, master, kit, textures=None, scalars=None, vectors=None, files=None, switches=None, note=""):
        R[name] = {"master": master, "kit": kit, "ue_dir": KITS[kit][2] + ("/Materials/Library" if kit == "library"
                                                                          else "/Materials"),
                   "textures": textures or {}, "scalars": scalars or {}, "vectors": vectors or {},
                   "switches": switches or {}, "note": note}
        for k, v in (files or {}).items():   # the library maps live once, in the library folder, whoever uses them
            TEX[k] = {"png": v, "ue_dir": (LIB[2] if k.startswith("T_DJ_") else KITS[kit][2]) + "/Textures",
                      "kind": k.rsplit("_", 1)[1]}

    def lib_tex(set_name):
        stem = f"T_DJ_{set_name}"
        files = {f"{stem}_{s}": str(LIB[1] / f"{stem}_{s}.png") for s in ("BC", "ORM", "N")}
        return {"BC": f"{stem}_BC", "ORM": f"{stem}_ORM", "N": f"{stem}_N"}, files

    def own_tex(kit, stem):
        d = KITS[kit][1]
        files = {f"{stem}_{s}": str(d / f"{stem}_{s}.png") for s in ("BC", "ORM", "N")}
        return {"BC": f"{stem}_BC", "ORM": f"{stem}_ORM", "N": f"{stem}_N"}, files

    wear_file = {"T_DJ_WearMask_M": str(LIB[1] / "T_DJ_WearMask_M.png")}

    def tile(set_name):
        t = djtg.SETS[set_name]["tile_m"] or (1.0, 1.0)
        return [float(t[0]), float(t[1]), 0.0, 0.0]

    def opaque(name, kit, t, f, set_for_tile, wear, tint=(1, 1, 1), rough=1.0, nstr=1.0, extra_s=None, extra_v=None,
               extra_sw=None, master="M_DJ_Lib_Opaque", tex_cm=None, note=""):
        sc = {"RoughMult": rough, "NormalStrength": nstr}
        vec = {"Tint": list(tint), "TileM": tile(set_for_tile)}
        tx = dict(t)
        files = dict(f)
        if wear:
            tx["WearMask"] = "T_DJ_WearMask_M"
            files.update(wear_file)
        if tex_cm is not None:
            sc["TextureSize"] = tex_cm
        sc.update(extra_s or {})
        vec.update(extra_v or {})
        add(name, master, kit, tx, sc, vec, files, dict({"UseWear": bool(wear)}, **(extra_sw or {})), note)

    # ---- the shared library, once per slot name (every kit that uses M_DJ_TimberDark shares one instance)
    for name in sorted(s for s in used_slots if s in djm.MATERIALS):
        spec = djm.MATERIALS[name]
        t, f = lib_tex(spec["set"])
        if spec["kind"] == "emissive":
            add(name, "M_DJ_Lib_Emissive", "library", t,
                {"EmissiveIntensity": spec["emission_strength"] * K_LUX, "BaseMult": spec.get("base_mult", 0.25),
                 "RoughMult": spec.get("rough_mult", 1.0), "NormalStrength": spec.get("normal_strength", 1.0)},
                {"EmissiveTint": [1.0, 1.0, 1.0]}, f, note="library emissive (README: GlassAmber 500, Vending 160)")
        elif name == "M_DJ_PlasterEarth":
            # kit 1's earthen wall plaster: world-aligned (build_kit1 lib_materials previews it in world space), so
            # wall modules of any length stay continuous
            if slot_kits.get(name, set()) - {"kit1"}:
                REPORT["warnings"].append(f"M_DJ_PlasterEarth is used outside kit 1 ({slot_kits[name]}): triplanar there too")
            opaque(name, "library", t, f, spec["set"], spec["wear"], master="M_DJ_Lib_Triplanar",
                   tex_cm=tile(spec["set"])[0] * 100.0, note="world-aligned (kit 1 wall plaster)")
        else:
            opaque(name, "library", t, f, spec["set"], spec["wear"], nstr=spec.get("normal_strength", 1.0))
    # ---- kit 1 variants (layout.json materials_kit1)
    mk = L1["materials_kit1"]
    if "M_DK_FootingStone" in used_slots:
        m = mk["M_DK_FootingStone"]
        tint = m["tint_linear"]
        flat, mean = _kit1_const("FS_FLAT"), _kit1_const("FS_MEAN")
        t, f = lib_tex(m["library"])
        opaque("M_DK_FootingStone", "kit1", t, f, m["library"], True, tint=tint,
               extra_s={"FlattenToMean": flat},
               extra_v={"MeanColour": [round(a * b, 5) for a, b in zip(mean, tint)],
                        "MossColour": list(m["moss"]["colour_linear"])},
               extra_sw={"UseMoss": True},
               note="library Granite x tint, lerp FS_FLAT to its (tinted) mean, moss by the 'Wear' alpha (build_kit1)")
    if "M_DK_TimberPale" in used_slots:
        # round 3 (kit 1 r3): the frame pier's pale weathered timber = library TimberAged x tint, lerped to its tinted
        # band mean (layout.json materials_kit1.M_DK_TimberPale: the M_DK_FootingStone branch without moss)
        m = mk["M_DK_TimberPale"]
        t, f = lib_tex(m["library"])
        opaque("M_DK_TimberPale", "kit1", t, f, m["library"], True, tint=m["tint_linear"],
               extra_s={"FlattenToMean": m["flatten_to_mean"]}, extra_v={"MeanColour": list(m["mean_linear"])},
               note="kit-1 pale timber: library TimberAged x tint, lerp flatten_to_mean to its tinted mean (build_kit1 r3)")
        R["M_DK_TimberPale"]["vectors"]["TileM"] = [float(m["tile_m"]), float(m["tile_m"]), 0.0, 0.0]
    for name in ("M_DK_EarthCore", "M_DK_JointEarth"):
        if name not in used_slots:
            continue
        m = mk[name]
        t, f = own_tex("kit1", f"T_DK_{m['texture']}")
        tint = hexcol(m["tint_srgb"]) if m.get("tint_srgb") else [1.0, 1.0, 1.0]
        opaque(name, "kit1", t, f, "PlasterEarth", False, tint=tint, master="M_DJ_Lib_Triplanar",
               tex_cm=m["tile_m"] * 100.0, note="kit 1 earth core, world-aligned as build_kit1 (world: True)")
    # ---- kit 2 ground
    for name, m in LG["materials"].items():
        if name not in used_slots:
            continue
        mac = m.get("macro", {})
        msc = {"Macro Tint": mac.get("tint", 0.0), "Macro Rough": mac.get("rough", 0.0), "Macro Dirt": mac.get("dirt", 0.0)}
        mfile = {"T_DKG_Macro_M": str(KITS["ground"][1] / "T_DKG_Macro_M.png")}
        if name == "M_DKG_Dressing":
            add(name, "M_DJ_Dressing_Master", "ground", scalars={"Roughness": m.get("roughness", 0.78)})
            continue
        if name == "M_DKG_Granite":
            t, f = lib_tex("Granite")
            hv = m["hue_var"]
            opaque(name, "ground", t, f, "Granite", True, tint=m["tint_lin"],
                   extra_s={"InstanceTint": m["instance_tint"]},
                   extra_v={"HueWarm": hv["warm"], "HueCool": hv["cool"]}, extra_sw={"UseInstanceVar": True},
                   note="ground instance of the library Granite: tint + per-actor tone / hue (Blender Object Info Random)")
            continue
        if name == "M_DKG_BedBlend":
            tg_, fg = own_tex("ground", "T_DKG_Gravel")
            ts_, fs_ = own_tex("ground", "T_DKG_Soil")
            tex = {"Gravel BC": tg_["BC"], "Gravel ORM": tg_["ORM"], "Gravel N": tg_["N"],
                   "Soil BC": ts_["BC"], "Soil ORM": ts_["ORM"], "Soil N": ts_["N"], "Macro Map": "T_DKG_Macro_M"}
            add(name, "M_DJ_BedBlend_Master", "ground", tex, dict(msc, **{"Blend Contrast": m.get("blend_contrast", 0.35),
                                                                          "Tile cm": 400.0}), {}, fg | fs_ | mfile)
            continue
        t, f = own_tex("ground", f"T_DKG_{m['texture']}")
        t = {"Base Colour Map": t["BC"], "ORM Map": t["ORM"], "Normal Map": t["N"], "Macro Map": "T_DKG_Macro_M"}
        if m.get("coords") == "world_xy":
            add(name, "M_DJ_GroundXY_Master", "ground", t, dict(msc, **{"Tile cm": m["tile"][0] * 100.0}), {}, f | mfile)
            continue
        if "normal_fade" in m:   # round 3: the rake normal fades with view distance (the moire guard, ground track)
            nf = m["normal_fade"]
            msc.update({"NormalFadeStart": nf["start_cm"], "NormalFadeEnd": nf["end_cm"],
                        "NormalFarStrength": nf["far_strength"]})
        add(name, "M_DJ_Ground_Master", "ground", t, dict(msc), {}, f | mfile)
    # ---- taiko: its own maps on the library graph (build_taiko: registered with the Lacquer set's 2 m tile)
    own = {"M_DKP_Taiko_Lacquer": "Lacquer", "M_DKP_Taiko_Hide": "Hide", "M_DKP_Taiko_HideCollar": "Collar"}
    for name, stem in own.items():
        if name in used_slots:
            t, f = own_tex("taiko", f"T_DKP_Taiko_{stem}")
            opaque(name, "taiko", t, f, "Lacquer", True, note="taiko-only set on the library graph (UseWear, TileM 2,2)")
    # ---- training: the rope fuzz variant (library Rope graph, UseWear off)
    if "M_DKP_Train_RopeFuzz" in used_slots:
        t, f = own_tex("training", "T_DKP_Train_RopeFuzz")
        opaque("M_DKP_Train_RopeFuzz", "training", t, f, "Rope", False, note="library Rope + fibre fuzz maps")
    # ---- stone: triplanar granite, moss pads, flat mortar / water
    for name, m in LP["stone"]["materials"].items():
        if name not in used_slots or name in R:
            continue
        p = m.get("params", {})
        if name == "M_DJ_Granite_Tri":
            spec = djm.MATERIALS[p["lib"]]
            t, f = lib_tex(spec["set"])
            opaque(name, "library", t, f, spec["set"], spec["wear"], master="M_DJ_Lib_Triplanar",
                   tex_cm=tile(spec["set"])[0] * 100.0, note="library granite, world-aligned (round / carved stone)")
        elif m["texture"] is None:
            add(name, "M_DJ_Flat_Master", "stone", scalars={"Roughness": p["rough"], "Metallic": 0.0, "Specular": 0.5},
                vectors={"Base Colour": hexcol(p["color"])})
        else:
            t, f = own_tex("stone", f"T_DKP_Stone_{m['texture']}")
            ts = djtg.SETS.get(m["texture"], {}).get("tile_m")
            opaque(name, "stone", t, f, "Granite", False, note=m.get("note", ""))
            R[name]["vectors"]["TileM"] = [float(m["tile_m"]), float(m["tile_m"]), 0.0, 0.0] if not ts else tile(m["texture"])
    # ---- modern kit-own
    for name, m in LP["modern"]["materials"].items():
        if name not in used_slots or name in R:
            continue
        if "textures" in m:
            stem = m["textures"][0].rsplit("_", 1)[0]
            t, f = own_tex("modern", stem)
            if "emissive" in m:
                k = float(re.search(r"x\s*([\d.]+)", m["emissive"]).group(1))
                add(name, "M_DJ_Lib_Emissive", "modern", t, {"EmissiveIntensity": k * K_LUX, "BaseMult": 1.0,
                                                              "RoughMult": 1.0, "NormalStrength": 1.0},
                    {"EmissiveTint": [1.0, 1.0, 1.0]}, f, note="opaque emissive: the hotspot is in the map")
            elif "masked" in m.get("blend", ""):
                tm = {"Base Colour Map": t["BC"], "ORM Map": t["ORM"], "Normal Map": t["N"]}
                add(name, "M_DJ_PropMasked_Master", "modern", tm, {}, {}, f)
            else:
                opaque(name, "modern", t, f, "Iron", False, note=m.get("family", ""))
                R[name]["vectors"]["TileM"] = [float(m.get("tile_m") or 1.0)] * 2 + [0.0, 0.0]
        elif "emit" in m:
            add(name, "M_DJ_EmissiveFlat_Master", "modern", scalars={"Roughness": 0.4, "Emissive Intensity": m["emit"] * K_LUX},
                vectors={"Base Colour": hexcol(m["color"]), "Emissive Colour": hexcol(m["emit_color"])})
        else:
            add(name, "M_DJ_Flat_Master", "modern", scalars={"Roughness": m.get("rough", 0.5), "Metallic": m.get("metal", 0.0),
                                                              "Specular": 0.5}, vectors={"Base Colour": hexcol(m["color"])})
    # ---- round 4: the kits' own instance recipes (the shed's two, layout_shed.json "materials"; no new textures:
    # their maps are the modern kit's galvanised set, the ground kit's soil + macro and the library wear mask)
    tex_home = {"T_DJ_": LIB[1], "T_DKG_": KITS["ground"][1], "T_DKP_Modern_": KITS["modern"][1]}
    for kit, LK in LR4.items():
        for name, m in LK.get("materials", {}).items():
            if name not in used_slots or name in R:
                continue
            R[name] = json.loads(json.dumps({k: m[k] for k in ("master", "kit", "ue_dir", "textures", "scalars", "vectors",
                                                                "switches", "note")}))
            for tname in m["textures"].values():
                if tname in TEX:
                    continue
                pre = next(p for p in tex_home if tname.startswith(p))
                own_kit = {"T_DJ_": "library", "T_DKG_": "ground", "T_DKP_Modern_": "modern"}[pre]
                TEX[tname] = {"png": str(tex_home[pre] / f"{tname}.png"),
                              "ue_dir": KITS[own_kit][2] + "/Textures", "kind": tname.rsplit("_", 1)[1]}
    missing = sorted(s for s in used_slots if s not in R and not s.startswith("M_DGB_"))
    if missing:
        raise RuntimeError(f"no material recipe for slots {missing}")
    bad = {k: v["png"] for k, v in TEX.items() if not Path(v["png"]).exists()}
    if bad:
        raise RuntimeError(f"missing texture files {bad}")
    # round 3: the Unreal look-pass instance values (showcase/look_r3.py, measured on the DojoLab captures)
    REPORT["look_r3"] = look_r3.apply_materials(R)
    return R, TEX, []


def material_recipes_round1(used_slots):
    """(round 1, retired 2026-09-28) slot name -> Unreal instance recipe (master, textures by parameter, scalars,
    vectors). Built from the kits' own material tables; emissive = Blender strength x K_LUX."""
    R, TEX = {}, {}

    def add(name, master, kit, textures=None, scalars=None, vectors=None, files=None, note=""):
        R[name] = {"master": master, "kit": kit, "ue_dir": KITS[kit][2] + "/Materials", "textures": textures or {},
                   "scalars": scalars or {}, "vectors": vectors or {}, "note": note}
        for k, v in (files or {}).items():
            TEX[k] = {"png": v, "ue_dir": KITS[kit][2] + "/Textures", "kind": k.rsplit("_", 1)[1]}

    # ---- kit 1
    for name, m in L1["materials_kit1"].items():
        p = m["params"]
        if m["texture"] is None:
            if "emit" in p:
                add(name, "M_DJ_EmissiveFlat_Master", "kit1", scalars={"Roughness": 0.4, "Emissive Intensity": p["emit"] * K_LUX},
                    vectors={"Base Colour": hexcol(p["color"]), "Emissive Colour": hexcol(p["emit_color"])})
            else:
                add(name, "M_DJ_Flat_Master", "kit1", scalars={"Roughness": p.get("rough", 0.8), "Metallic": 0.0, "Specular": 0.5},
                    vectors={"Base Colour": hexcol(p["color"])})
            continue
        t, f = tset("kit1", f"T_DK_{m['texture']}")
        sc = {"Grime": p.get("grime", 0.0)}
        vec = {"Grime Colour": hexcol(p.get("grime_color", "#6A5A48"))}
        if p.get("world"):
            t.pop("Normal Map")
            sc["Tile cm"] = m["tile_m"] * 100.0
            add(name, "M_DJ_K1World_Master", "kit1", t, sc, vec, f, "world-aligned (triplanar) as the Blender material")
        else:
            sc.update({"Moss": 1.0 if p.get("moss") else 0.0, "Crest": 1.0 if p.get("crest") else 0.0})
            t2 = dict(t)
            if p.get("moss"):
                t2["Moss Mask"] = "T_DK_MossMask_M"
                f["T_DK_MossMask_M"] = str(KITS["kit1"][1] / "T_DK_MossMask_M.png")
            add(name, "M_DJ_K1_Master", "kit1", t2, sc, vec, f)
    # ---- kit 2 ground
    for name, m in LG["materials"].items():
        mac = m.get("macro", {})
        msc = {"Macro Tint": mac.get("tint", 0.0), "Macro Rough": mac.get("rough", 0.0), "Macro Dirt": mac.get("dirt", 0.0)}
        mfile = {"T_DKG_Macro_M": str(KITS["ground"][1] / "T_DKG_Macro_M.png")}
        if name == "M_DKG_Dressing":
            add(name, "M_DJ_Dressing_Master", "ground", scalars={"Roughness": m.get("roughness", 0.78)})
            continue
        if name == "M_DKG_BedBlend":
            tg, fg = tset("ground", "T_DKG_Gravel")
            ts, fs = tset("ground", "T_DKG_Soil")
            tex = {"Gravel BC": tg["Base Colour Map"], "Gravel ORM": tg["ORM Map"], "Gravel N": tg["Normal Map"],
                   "Soil BC": ts["Base Colour Map"], "Soil ORM": ts["ORM Map"], "Soil N": ts["Normal Map"],
                   "Macro Map": "T_DKG_Macro_M"}
            add(name, "M_DJ_BedBlend_Master", "ground", tex, dict(msc, **{"Blend Contrast": m.get("blend_contrast", 0.35),
                                                                          "Tile cm": 400.0}), {}, fg | fs | mfile)
            continue
        t, f = tset("ground", f"T_DKG_{m['texture']}")
        t["Macro Map"] = "T_DKG_Macro_M"
        if m.get("coords") == "world_xy":
            add(name, "M_DJ_GroundXY_Master", "ground", t, dict(msc, **{"Tile cm": m["tile"][0] * 100.0}), {}, f | mfile)
            continue
        sc = dict(msc)
        vec = {}
        if "wear_dark" in m:
            sc.update({"Wear Dark": m["wear_dark"], "Wear On": 1.0, "Instance Tint": m.get("instance_tint", 0.0),
                       "Hue Var": 1.0, "Crown Gloss": m.get("crown_gloss", 0.0)})
            vec = {"Hue Warm": m["hue_var"]["warm"], "Hue Cool": m["hue_var"]["cool"]}
        add(name, "M_DJ_Ground_Master", "ground", t, sc, vec, f | mfile)
    # ---- props
    for name, m in LP["taiko"]["materials"].items():
        t, f = tset("taiko", m["texture_set"])
        add(name, "M_DJ_Prop_Master", "taiko", t, {}, {}, f)
    wear = {"M_DKP_Train_Timber": (0.80, 0.85, 0.35, 0.0), "M_DKP_Train_TimberEnd": (0.80, 0.85, 0.35, 0.0),
            "M_DKP_Train_Iron": (0.55, 0.55, 0.30, 1.0), "M_DKP_Train_Rope": (0.35, 0.0, 0.25, 0.0)}
    for name in LP["training"]["materials"]:
        t, f = tset("training", name.replace("M_", "T_", 1))
        kg, kw, kd, metal = wear[name]
        add(name, "M_DJ_Prop_Master", "training", t,
            {"AO To Base": 1.0, "VC Grime": kg, "VC Wear": kw, "VC Dust": kd, "Worn Metal": metal,
             "Grime Rough": 0.08, "Wear Rough": 0.12},
            {"Grime Colour": [0.012, 0.008, 0.005], "Dust Colour": [0.16, 0.13, 0.10], "Worn Colour": [0.30, 0.29, 0.27]},
            f, "training 'Wear' vertex colour: R grime, G edge wear, B ground dirt (build_training_props.py)")
    for name, m in LP["stone"]["materials"].items():
        p = m.get("params", {})
        if m["texture"] is None:
            add(name, "M_DJ_Flat_Master", "stone", scalars={"Roughness": p["rough"], "Metallic": 0.0, "Specular": 0.5},
                vectors={"Base Colour": hexcol(p["color"])})
            continue
        t, f = tset("stone", f"T_DKP_Stone_{m['texture']}")
        if "emit" in p:
            add(name, "M_DJ_EmissiveTex_Master", "stone", t, {"Emissive Intensity": p["emit"] * K_LUX}, {}, f)
        else:
            add(name, "M_DJ_Prop_Master", "stone", t, {}, {}, f)
    for name, m in LP["modern"]["materials"].items():
        if "textures" in m:
            stem = m["textures"][0].rsplit("_", 1)[0]
            t, f = tset("modern", stem)
            if "emissive" in m:
                k = float(re.search(r"x\s*([\d.]+)", m["emissive"]).group(1))
                add(name, "M_DJ_EmissiveTex_Master", "modern", t, {"Emissive Intensity": k * K_LUX}, {}, f,
                    "opaque emissive: the hotspot is in the map (Nanite-safe; no translucent glass)")
            elif "masked" in m.get("blend", ""):
                add(name, "M_DJ_PropMasked_Master", "modern", t, {}, {}, f)
            else:
                add(name, "M_DJ_Prop_Master", "modern", t, {}, {}, f)
        elif "emit" in m:
            add(name, "M_DJ_EmissiveFlat_Master", "modern", scalars={"Roughness": 0.4, "Emissive Intensity": m["emit"] * K_LUX},
                vectors={"Base Colour": hexcol(m["color"]), "Emissive Colour": hexcol(m["emit_color"])})
        else:
            add(name, "M_DJ_Flat_Master", "modern", scalars={"Roughness": m.get("rough", 0.5), "Metallic": m.get("metal", 0.0),
                                                              "Specular": 0.5}, vectors={"Base Colour": hexcol(m["color"])})
    missing = sorted(s for s in used_slots if s not in R and not s.startswith("M_DGB_"))
    if missing:
        raise RuntimeError(f"no material recipe for slots {missing}")
    bad = {k: v["png"] for k, v in TEX.items() if not Path(v["png"]).exists()}
    if bad:
        raise RuntimeError(f"missing texture files {bad}")
    unused = sorted(k for k in R if k not in used_slots)
    return {k: v for k, v in R.items() if k in used_slots}, TEX, unused


# ------------------------------------------------------------------------------------------------ lights, cameras, sun
def lamp_lights(instances, kit_objs):
    out = []
    for n, i in enumerate(instances):
        if i["piece"] not in LAMP_LIGHTS:
            continue
        slot, watt, kelvin, radius = LAMP_LIGHTS[i["piece"]]
        ob = kit_objs[i["piece"]]
        si = [strip(s.material.name) for s in ob.material_slots].index(slot)
        pts = [ob.data.vertices[v].co for p in ob.data.polygons if p.material_index == si for v in p.vertices]
        c = Vector([(min(p[k] for p in pts) + max(p[k] for p in pts)) / 2 for k in range(3)])
        w = matrix_of(i) @ c
        out.append({"name": f"Light_{i['piece'].replace('SM_', '')}__{n:04d}", "instance": n, "loc": rnd(w, 4),
                    "candela": round(K_LUX * watt / (4 * math.pi), 2), "kelvin": kelvin, "radius_m": radius,
                    "shadows": False, "source": f"{slot} centre, {watt} W Blender review power x K {K_LUX:.0f} / 4 pi"})
    return out


def sun():
    el, az = 13.0, 160.0    # showcase: 13 deg (grey-box 7): long shadows but the fields stay lit, from the W-N-W
    to_sun = Vector((math.cos(math.radians(el)) * math.cos(math.radians(az)),
                     math.cos(math.radians(el)) * math.sin(math.radians(az)), math.sin(math.radians(el))))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import marker_policy   # round 2: the sun temperature and its note live beside the marker fixes
    return {"type": "sun", "name": "Sun_Sunset", "elev_deg": el, "azimuth_deg_from_x": az,
            "kelvin": marker_policy.SUN_KELVIN, "travel_dir": rnd(-to_sun, 5), "lux": round(4.2 * K_LUX, 1),
            "note": marker_policy.SUN_NOTE,
            "exposure_bias": round(0.6 - math.log2(K_LUX), 4)}


CAMERAS = [   # name, loc, look_at, hfov, (w, h), note  (Blender frame, metres)
    ("CAM_GateFromCourtyard", (22.0, 13.5, 1.65), (22.0, 0.0, 2.7), 62.0, (1920, 1080),
     "the gate from the courtyard, player eye on the path"),
    ("CAM_Establishing", (22.0, 0.25, 2.3), (22.0, 30.0, 0.9), 74.0, (1448, 1086),
     "from the gate threshold toward the hall (dojo1_reference2's framing and aspect; round 4 f1: moved from under the "
     "gate roof (Y -1.6), where its beams hid the whole hall roof, to the courtyard side of the leaves)"),
    ("CAM_PlayerEyeSand", (16.5, 4.5, 1.65), (21.5, 26.0, 2.4), 70.0, (1920, 1080),
     "player eye on the raked sand toward the hall"),
    ("CAM_Drum", (36.3, 4.6, 2.1), (41.0, 2.9, 1.95), 52.0, (1920, 1080),
     "the taiko under the pavilion, from the courtyard side (ring handle)"),
    ("CAM_EstablishingRef2", (22.0, 2.9, 3.1), (22.0, 24.0, 0.3), 74.0, (1448, 1086),
     "round 2: dojo1_reference2's elevated framing as kit 1's beauty_ref2 (3.1 m, just past the gate's courtyard "
     "eave, so the hall's upper roof shows; the reference itself is not physically consistent with a real gate roof)"),
    ("CAM_EastYard", (43.3, 19.5, 1.85), (33.5, 23.0, 1.3), 84.0, (1920, 1080),
     "the east yard (round 2): the well in front, the residence wall lamp, the east tall lantern at the hall steps"),
    ("CAM_HallVeranda", (24.6, 17.4, 1.6), (19.5, 22.6, 1.0), 68.0, (1920, 1080),
     "round 2: the hall kit close: the granite step band with its wide central stair, the veranda, posts and bays"),
    ("CAM_HallRoofClimb", (11.4, 18.4, 5.2), (15.0, 22.2, 3.8), 75.0, (1920, 1080),
     "round 2: routes 4-5 on the hall kit: the west eave landing deck, the lower roof, the roof AC (+5.10), the upper "
     "eave"),
    ("CAM_VendingShed", (16.2, 6.8, 1.7), (8.0, 1.2, 1.2), 70.0, (1920, 1080), "the vending machine / shed corner"),
    ("CAM_GateFromStreet", (22.0, -13.5, 1.7), (22.0, 0.0, 3.0), 64.0, (1920, 1080), "the gate from the street"),
    ("CAM_WallTop", (-0.5, 2.0, 3.62), (-0.3, 30.0, 2.9), 72.0, (1920, 1080),
     "a player's eye along the west wall top (the grey-box tree canopy stands beside it)"),
    ("CAM_WallCorner", (47.9, -3.9, 1.45), (44.6, -0.6, 1.15), 56.0, (1920, 1080), "the SE wall corner from outside"),
    ("CAM_Overview", (22.0, -17.0, 27.0), (22.0, 15.0, 0.0), 70.0, (1920, 1080), "overview from above the gate (ref 1)"),
    # round 3: close-ups for the look judges (all in showcase/look_r3.py CLOSEUPS: one list for compose and the patch)
] + [tuple(c) for c in look_r3.CLOSEUPS]


# ------------------------------------------------------------------------------------------------ main
def main():
    reset_scene()
    SC.mkdir(parents=True, exist_ok=True)
    P = piece_table()
    kit_objs, meta = {}, {}
    for name, p in P.items():
        if name == PAVILION_NODRUM:
            continue
        if not Path(p["fbx"]).exists():
            raise RuntimeError(f"missing export {p['fbx']}")
        meta[name] = import_piece(name, p["fbx"])
        kit_objs[name] = bpy.data.objects[name]
    # the pavilion without its drum (from the grey-box export); round 4: gone, the pavilion kit replaces it
    if PAVILION_NODRUM in P:
        compose_nodrum(P, meta, kit_objs)
    finish_main(P, meta, kit_objs)


def compose_nodrum(P, meta, kit_objs):
    meta["SM_DGB_Pavilion"] = import_piece("SM_DGB_Pavilion", EXP / "SM_DGB_Pavilion.fbx")
    src = bpy.data.objects["SM_DGB_Pavilion"]
    nd = make_nodrum(src)
    for h in list(src.children):
        bpy.data.objects.remove(h, do_unlink=True)
    bpy.data.objects.remove(src, do_unlink=True)
    meta.pop("SM_DGB_Pavilion")
    kit_objs[PAVILION_NODRUM] = nd
    mb = world_bbox(nd)
    meta[PAVILION_NODRUM] = {"slots": [strip(s.material.name) for s in nd.material_slots], "tris": tri_count(nd),
                             "lod_tris": [tri_count(nd)], "lods": 1,
                             "ucx": sorted(h.name for h in nd.children if h.name.startswith("UCX_")),
                             "n_ucx": sum(1 for h in nd.children if h.name.startswith("UCX_")), "vcol": [],
                             "bbox_lod0": [rnd(mb[0], 5), rnd(mb[1], 5)], "bbox_all_lods": [rnd(mb[0], 5), rnd(mb[1], 5)],
                             "ucx_bbox": None}


def finish_main(P, meta, kit_objs):
    for name, p in P.items():
        p.update({k: meta[name][k] for k in ("slots", "tris", "lod_tris", "lods", "n_ucx", "vcol")})
        if p["kit"] not in ("kit1", "greybox", "showcase", "ground", "hall") + R4_KITS:
            p["nanite"] = p["tris"] > NANITE_MIN_TRIS and p["class"] != "nocollision"
    # instances
    base = base_instances()
    ground, _bvh = ground_vs_paving(ground_instances(P), kit_objs, base)
    props = prop_instances()
    hall = hall_instances()
    # round 2: the short lanterns stand on whatever floor is under them (ray cast on the ground kit + the gate paving)
    floor_src = [i for i in ground + base if i["kit"] == "ground" or i["piece"] == "SM_DK_Gate_Paving"]
    gate_roof = next(i for i in base if i["piece"] == "SM_DK_Gate_Roof")
    gr_box = world_bbox(kit_objs["SM_DK_Gate_Roof"], matrix_of(gate_roof))
    REPORT["short_lanterns"] = []
    for i in props:
        if i["piece"] == "SM_DKP_Stone_LanternShort":
            z, under = floor_at(i["loc"][0], i["loc"][1], floor_src, kit_objs)
            if z is not None:
                i["loc"][2] = round(z, 4)
                i["note"] = f"on {under} (+{z:.3f}, ray cast): " + i["note"]
            lb = world_bbox(kit_objs[i["piece"]], matrix_of(i))
            REPORT["short_lanterns"].append({"loc": rnd(i["loc"], 4), "floor": under, "bbox": [rnd(lb[0], 3), rnd(lb[1], 3)],
                                             "gate_roof_max_y": round(gr_box[1][1], 4),
                                             "clear_of_gate_roof_m": round(lb[0][1] - gr_box[1][1], 4)})
            if lb[0][1] <= gr_box[1][1]:
                raise RuntimeError(f"short lantern at {i['loc']} is under the gate roof (roof max Y {gr_box[1][1]:.3f})")
    REPORT["fits"] = fit_climb_props(props, meta)
    REPORT["round4_prop_moves"] = apply_prop_moves(props)
    r4 = round4_instances()
    # round 4: the ground kit's own gravel panels in the strips its layout left at the grey-box footprints (round4.py)
    fill = [inst(pc, (x, y, 0.0), 0.0, "ground", "Ground/Gravel", P[pc]["class"], source="round4.GROUND_FILL",
                 note="round 4 fill: the ground kit stopped at the grey-box building footprint") for pc, x, y in round4.GROUND_FILL]
    REPORT["round4_ground_fill"] = [[pc, x, y] for pc, x, y in round4.GROUND_FILL]
    instances = base + ground + props + hall + r4 + fill
    # round 3 (user 2026-09-28: "drop the invented lamps"): no street lamp inside the courtyard, no short lantern at all
    REPORT["dropped_lamps_check"] = look_r3.check_no_invented_lamps(instances)
    for i in instances:
        i.pop("bbox_layout", None)
        i["folder"] = i["folder"] or P[i["piece"]]["folder"]
        i["collision_class"] = i["collision_class"] or P[i["piece"]]["class"]
        if P[i["piece"]]["class"] != i["collision_class"]:
            REPORT["warnings"].append(f"{i['piece']}: instance class {i['collision_class']} != piece class "
                                      f"{P[i['piece']]['class']}")
    # re-fit the weapon-rack markers to the real rack's top rail (GASP ledges = the marker's top edges)
    markers = json.loads(json.dumps(L1["traversal_markers"]))
    rack = kit_objs["SM_DKP_Train_WeaponRack"]
    hull_boxes = sorted((world_bbox(h, h.matrix_local) for h in rack.children if h.name.startswith("UCX_")),
                        key=lambda b: -b[1][2])
    REPORT["weapon_rack_hulls_local"] = [[rnd(b[0], 4), rnd(b[1], 4)] for b in hull_boxes]
    for mname, side in (("WeaponRack_W", 4.0), ("WeaponRack_E", 40.0)):
        ri = next(i for i in props if i["piece"] == "SM_DKP_Train_WeaponRack" and abs(i["loc"][0] - side) < 0.5)
        top = hull_boxes[0]
        mw = matrix_of(ri)
        pts = [mw @ Vector((x, y, z)) for x in (top[0][0], top[1][0]) for y in (top[0][1], top[1][1])
               for z in (top[0][2], top[1][2])]
        box = [min(p.x for p in pts), max(p.x for p in pts), min(p.y for p in pts), max(p.y for p in pts), 0.0,
               max(p.z for p in pts)]
        m = next(m for m in markers if m["name"] == mname)
        REPORT["fits"][mname] = {"grey_box": m["box"], "refit": rnd(box, 4)}
        m["box"] = rnd(box, 4)
        m["note"] = f"weapon rack top rail +{box[5]:.3f} (refit to the kit's highest UCX hull; grey-box box was 1.2 x 0.4)"
    # re-fit the roof-AC markers to the kit AC's casing hull (top +5.10 after the Z fit; its front face is at Y 21.98,
    # 12 cm in front of the grey-box box, so GASP's room point 32 cm out from a 22.1 ledge would sit inside the casing)
    ac_obj = kit_objs["SM_DKP_Modern_ACUnit_Roof"]
    for mname in ("ACUnit_W", "ACUnit_E"):
        m = next(m for m in markers if m["name"] == mname)
        ai = next(i for i in props if i["piece"] == "SM_DKP_Modern_ACUnit_Roof" and m["box"][0] - 0.01 <= i["loc"][0] <= m["box"][1] + 0.01)
        mw = matrix_of(ai)
        top = max((world_bbox(h, mw @ h.matrix_local) for h in ac_obj.children if h.name.startswith("UCX_")),
                  key=lambda b: b[1][2])
        box = [top[0][0], top[1][0], top[0][1], top[1][1], m["box"][4], top[1][2]]
        REPORT["fits"][mname] = {"grey_box": m["box"], "refit": rnd(box, 4)}
        m["box"] = rnd(box, 4)
        m["note"] = f"kit AC casing top +{box[5]:.2f} (refit to its casing hull; grey-box box Y 22.1-23.1)"
    # round 2: the vending machine at its true 0.80 m depth: the Vending marker = its UCX box (flush flat top +1.75)
    vi = next(i for i in props if i["piece"] == "SM_DKP_Modern_VendingMachine")
    vb = ucx_world_box(kit_objs[vi["piece"]], matrix_of(vi))
    m = next(m for m in markers if m["name"] == "Vending")
    box = [vb[0][0], vb[1][0], vb[0][1], vb[1][1], 0.0, vb[1][2]]
    REPORT["fits"]["Vending"] = {"grey_box": m["box"], "refit": rnd(box, 4), "loc": vi["loc"], "scale": vi["scale"]}
    m["box"] = rnd(box, 4)
    m["note"] = f"kit vending machine UCX box at its true depth ({box[3] - box[2]:.3f} m), top +{box[5]:.3f} (unscaled)"
    # round 2: the hall kit. Veranda +0.5 (the deck starts at Y 22.0 behind the step band, as build_hall's check layout);
    # the eave-landing markers = the SM_DKH_EaveLanding decks' UCX boxes (flat top +3.0, route 4)
    hn = LH["numbers"]
    m = next(m for m in markers if m["name"] == "Hall_Veranda")
    vx0, vx1, vy0, vy1 = hn["veranda"]
    REPORT["fits"]["Hall_Veranda"] = {"grey_box": m["box"], "refit": [vx0, vx1, vy0, vy1, 0.0, hn["floor"]]}
    m["box"] = [vx0, vx1, vy0, vy1, 0.0, hn["floor"]]
    m["note"] = "hall kit veranda +0.5 from the side yards (the deck starts at Y 22.0 behind the step band)"
    el = kit_objs["SM_DKH_EaveLanding"]
    for side in ("W", "E"):
        m = next(m for m in markers if m["name"] == f"Landing_EavePad_{side}")
        cands = [i for i in hall if i["piece"] == "SM_DKH_EaveLanding"
                 and m["box"][0] - 0.3 <= ucx_world_box(el, matrix_of(i))[0][0] <= m["box"][1]]
        if len(cands) != 1:
            raise RuntimeError(f"eave landing {side}: {len(cands)} candidates")
        b = ucx_world_box(el, matrix_of(cands[0]))
        box = [b[0][0], b[1][0], b[0][1], b[1][1], m["box"][4], b[1][2]]
        REPORT["fits"][m["name"]] = {"grey_box": m["box"], "refit": rnd(box, 4), "hall_numbers": hn["eave_landings"][side]}
        m["box"] = rnd(box, 4)
        m["note"] = f"hall kit eave landing deck UCX, flat top +{box[5]:.3f} (route 4)"
    climb_routes = json.loads(json.dumps(L1["climb_routes"]))
    for r in climb_routes:
        if r.get("marker") in ("ACUnit_W", "ACUnit_E"):   # the stance stands on the hall kit's lower roof
            r["floor_z"] = hn["ac_zones"]["stance"]["floor_z"]
    for r in climb_routes:   # the hurdle stance must stand clear of the real rack (its front face moved west)
        if r.get("marker") == "WeaponRack_W":
            mb_ = next(m for m in markers if m["name"] == "WeaponRack_W")["box"]
            rb = ucx_world_box(rack, matrix_of(next(i for i in props if i["piece"] == "SM_DKP_Train_WeaponRack"
                                                    and abs(i["loc"][0] - 4.0) < 0.5)))
            new_x = round(min(mb_[0], rb[0][0]) - 0.36, 3)
            REPORT["fits"]["hurdle_stance"] = {"grey_box": r["stance"], "new": [new_x, r["stance"][1]],
                                               "rack_front_x": round(rb[0][0], 4)}
            r["stance"] = [new_x, r["stance"][1]]
        if r.get("marker") in ("ACUnit_W", "ACUnit_E"):   # the kit AC's stand hull starts at Y 21.98 (grey-box box 22.1)
            ac = next(i for i in props if i["piece"] == "SM_DKP_Modern_ACUnit_Roof"
                      and abs(i["loc"][0] - r["stance"][0]) < 0.7)
            ab = ucx_world_box(kit_objs[ac["piece"]], matrix_of(ac))
            new_y = round(ab[0][1] - 0.30 - 0.02, 3)
            REPORT["fits"]["ac_stance_" + r["marker"]] = {"grey_box": r["stance"], "new": [r["stance"][0], new_y],
                                                          "stand_front_y": round(ab[0][1], 4)}
            r["stance"] = [r["stance"][0], new_y]
    REPORT["round4_f1_climb_routes"] = round4.apply_climb_f1(climb_routes)   # f1: gable-front outbuildings
    # round 2 (2026-09-28): pavilion-pad bottom +1.50, stale gate-side wall markers removed (marker_policy.py)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import marker_policy
    REPORT["round4_marker_fits"] = fit_round4_markers(markers, r4, kit_objs)
    _, REPORT["marker_policy"] = marker_policy.apply(markers, climb_routes)
    REPORT["marker_vs_prop"] = check_markers(instances, kit_objs)
    walk = json.loads(json.dumps(L1["walk_routes"]))
    walk["CONTROL_1v1_ring_at_the_open_gate"] = dict(walk.pop("CONTROL_through_the_closed_gate"),
                                                     note="the leaves stand OPEN in the showcase: the 1v1 ring on the "
                                                          "wall's outer face is what stops a 1v1 player at the gate")
    REPORT["round4_walk_routes"] = sorted(round4.walk_routes(walk))
    walk.update(round4.walk_routes(walk))
    # Assembly (instances named <piece>__<nnnn>) + bounds
    bounds = {}
    for n, i in enumerate(instances):
        src_o = kit_objs[i["piece"]]
        o = bpy.data.objects.new(f"{i['piece']}__{n:04d}", src_o.data)
        ASM_COLL.objects.link(o)
        o.matrix_world = matrix_of(i)
        lb = meta[i["piece"]]["bbox_lod0"]
        corners = [Vector((x, y, z)) for x in (lb[0][0], lb[1][0]) for y in (lb[0][1], lb[1][1]) for z in (lb[0][2], lb[1][2])]
        w = [o.matrix_world @ c for c in corners]
        bounds[str(n)] = {"piece": i["piece"], "min": rnd([min(p[k] for p in w) for k in range(3)], 5),
                          "max": rnd([max(p[k] for p in w) for k in range(3)], 5)}
        # round 2: UE's render bounds of a non-Nanite mesh are the union of ALL its LODs (a decimated LOD can bulge
        # past LOD0: SM_DKH_StepBand's LOD1 by 3.6 cm), so the Unreal gates compare those against this box
        la = meta[i["piece"]]["bbox_all_lods"]
        wa = [o.matrix_world @ Vector((x, y, z)) for x in (la[0][0], la[1][0]) for y in (la[0][1], la[1][1])
              for z in (la[0][2], la[1][2])]
        bounds[str(n)]["min_all_lods"] = rnd([min(p[k] for p in wa) for k in range(3)], 5)
        bounds[str(n)]["max_all_lods"] = rnd([max(p[k] for p in wa) for k in range(3)], 5)
    KIT_COLL.hide_render = True
    for o in KIT_COLL.objects:
        o.hide_set(True)
    used = sorted({s for p in P.values() for s in p["slots"] if s})
    slot_kits = {}
    for p in P.values():
        for s_ in p["slots"]:
            if s_:
                slot_kits.setdefault(s_, set()).add(p["kit"])
    recipes, textures, unused = material_recipes(used, slot_kits)
    lights = lamp_lights(instances, kit_objs)
    REPORT["lamp_tune_r3"] = look_r3.apply_lights(lights)   # round 3: the gate lamps 3000 K x2 (look_r3.LAMP_TUNE)
    k1 = [l for l in lights if "Gate_Lamp" in l["name"]]
    REPORT["gate_lamp_light_vs_kit1"] = [[l["loc"], L1["kit1"]["lamp_lights_world"][j]] for j, l in enumerate(k1)]
    counts = {}
    for i in instances:
        counts[i["kit"]] = counts.get(i["kit"], 0) + 1
    layout = {
        "units": L1["units"], "spec": L1["spec"], "date": "2026-09-28", "stage": "showcase",
        "sources": {"layout": "layout.json (grey-box + kit 1 r2f)", "ground": "ground/layout_ground.json (kit 2 r2)",
                    "props": {k: f"props/{k}/layout_{k}.json" for k in PROP_KEYS},
                    "hall": "hall/layout_hall.json (kits 3 + 4 f1; round-4 ridges)",
                    "round4": {k: v.relative_to(BUILD).as_posix() for k, v in round4.LAYOUT_FILES.items()}},
        "round": "showcase r4 (combined import round 4, the remaining buildings, 2026-09-29)", "hall": LH["numbers"],
        "round4_numbers": {k: v.get("numbers", {}) for k, v in LR4.items()},
        "retired_meshes": look_r3.RETIRED_MESHES,
        "k_lux": K_LUX, "pieces": P, "instances": instances, "collision_classes": dict(L1["collision_classes"], **COLLISION_EXTRA),
        "materials": recipes, "textures": textures, "traversal_markers": markers, "player_starts": L1["player_starts"],
        "sun": sun(), "lights": lights,
        "cameras": [{"name": c[0], "loc": list(c[1]), "look_at": list(c[2]), "hfov_deg": c[3], "out_wh": list(c[4]),
                     "note": c[5]} for c in CAMERAS],
        "climb_routes": climb_routes, "walk_routes": walk, "numbers": L1["numbers"], "kit1": L1["kit1"],
        "replaced_greybox": sorted(set(REPLACED_GB) | set(L1["kit1"]["replaced_greybox"]) | {"SM_DGB_Pavilion"}),
        "greybox_kept": sorted({i["piece"] for i in instances if i["kit"] == "greybox"}),
        "not_placed": {"SM_DK_Wall_FramePier": "kit piece for the BR wall openings (kit1.frame_pier)",
                       "SM_DKP_Stone_WellFrameGable": "SPARE (user 2026-10-02): imported, not placed (BR village)",
                       "SM_DKP_Stone_CrateHalf": "stacking / dressing piece (no layout position)",
                       "SM_DKP_Stone_LanternShort": "SPARE (user 2026-09-28: drop the invented lamps; no short "
                                                    "lanterns inside the gate)",
                       "SM_DKP_Modern_StreetLamp_B": "SPARE (user 2026-09-28: no street lamps inside the courtyard; "
                                                     "street lamp A stands outside on the street, as reference 1)",
                       "SM_DKG_Kerb25_*, Kerb50_Corner, SandEdging/..": "ground kit pieces the ground layout does not place"},
        "counts": {"pieces": len(P), "instances": len(instances), "per_kit": counts, "lights": len(lights),
                   "materials": len(recipes), "textures": len(textures)},
    }
    (SC / "layout_showcase.json").write_text(json.dumps(layout, indent=1), encoding="utf-8")
    (SC / "blender_bounds.json").write_text(json.dumps(
        {"blend": str(BLEND), "instances": bounds, "n_instances": len(bounds),
         "pieces": {k: {kk: v[kk] for kk in ("slots", "tris", "lod_tris", "lods", "ucx", "n_ucx", "vcol", "bbox_lod0",
                                              "bbox_all_lods", "ucx_bbox")} for k, v in meta.items()}}, indent=1),
        encoding="utf-8")
    REPORT["counts"] = layout["counts"]
    REPORT["unused_recipes"] = unused
    REPORT["placed_pieces"] = len({i["piece"] for i in instances})
    REPORT["imported_not_placed"] = sorted(set(P) - {i["piece"] for i in instances})
    (SC / "compose_report.json").write_text(json.dumps(REPORT, indent=1, default=str), encoding="utf-8")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("SHOWCASE_COMPOSED", json.dumps(layout["counts"]), "warnings", len(REPORT["warnings"]))


main()
