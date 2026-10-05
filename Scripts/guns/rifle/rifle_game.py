"""AR-01 stage 4: the static twin SM_AR01 (headless Blender):

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_game.py

- game materials M_AR01_Metal (0), M_AR01_Furniture (1), M_AR01_Mag (2) on the painted maps (Exports/Guns/AR01/Textures)
- SM_AR01_LOD0..3: each LOD's parts joined (LOD0 = AR01_Parts, LOD1-2 = the same generators at gunlib.lod levels 1-2,
  LOD3 = the blockout generator), the merged magazine copy included (the user's default); UV0 slot k on U tile k
  (Metal 0..1, Furniture 1..2, Mag -1..0; the skeletal parts keep every set in 0..1); UV1 = each set's layout scaled
  into its own square of 0..1 (authored fallback; Unreal regenerates UV1 at import)
- 7 hulls UCX_SM_AR01_LOD0_00..06 (RIFLE_BUILD_PLAN 7.1; spec collision_static_twin) from dense surface samples of
  every LOD (LOD0 <= 1 mm, LOD1-2 <= 2 mm, LOD3 vertices), neighbours overlapping 3 mm along the barrel line,
  <= 32 vertices, dilated 0.2 mm, grown until every sample is inside
- 17 sockets (GUN_BUILDING_STUDY 5.3 names; spec values; CenterOfMass computed from part volumes x densities, Holster =
  CenterOfMass) as Empties on LOD0 (helpers.make_socket: Unreal orientation authored, 180-degree correction)
- the LOD group (helpers.make_lod_group) with the LOD screen sizes stored on it (sidecar at export: the gate sets them)
Writes scratch/game/game_report.json and scratch/game/lod<k>_tris.npz (per-part labels; for S2 and the LOD-pop gate)
and saves Assets/Guns/AR01.blend.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SCRATCH, BLEND, GRIP, SPEC  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import rifle_surface as RS  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import bl  # noqa: E402

sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline.helpers import make_lod_group, make_socket  # noqa: E402

NAME = "SM_AR01"
OUT = SCRATCH / "game"
OUT.mkdir(parents=True, exist_ok=True)
TEX = ROOT / "Exports" / "Guns" / "AR01" / "Textures"
SLOTS = ("M_AR01_Metal", "M_AR01_Furniture", "M_AR01_Mag")
SLOT_INDEX = {s: i for i, s in enumerate(SLOTS)}
TILE = {0: 0.0, 1: 1.0, 2: -1.0}
UV1_REGIONS = {0: (0.0, 0.0, 0.62), 1: (0.625, 0.0, 0.375), 2: (0.625, 0.38, 0.375)}
SCREEN_SIZES_START = [1.0, 0.30, 0.12, 0.04]

# hull groups (RIFLE_BUILD_PLAN 7.1); the round parts along the barrel line split by X (frame M) with 3 mm overlaps
HULLS = [
    ("receiver, dust cover, rear sight, selector, carrier + handle",
     ("receiver", "rear_trunnion", "dust_cover", "recoil_spring_button", "rivets", "receiver_rails", "bolt_carrier",
      "rear_sight_block", "rear_sight_leaf", "rear_sight_slider", "selector"), None),
    ("fore-end: handguards, front band, retainer, cap; barrel, gas tube, rod to the gas block",
     ("upper_handguard", "lower_handguard", "handguard_front_band", "handguard_retainer", "gas_tube_rear_cap"),
     (None, 684.0)),
    ("gas block section: gas block, exposed barrel, gas tube front, rod", ("gas_block",), (678.0, 809.0)),
    ("front sight block + post + brake", ("front_sight_block", "front_sight_post", "muzzle_brake"), (803.0, None)),
    ("pistol grip + trigger guard + trigger + catch", ("pistol_grip", "trigger_guard", "trigger", "mag_catch"), None),
    ("stock + butt plate + swivel + hardware",
     ("buttstock", "butt_plate", "butt_screws", "sling_swivel_base", "sling_swivel_loop", "stock_hardware",
      "sling_swivel_rear"), None),
    ("merged magazine (twin only)", ("magazine", "magazine_floor_plate"), None),
]
LINE_PARTS = ("barrel", "gas_tube", "gas_piston", "cleaning_rod")
DENSITY = {"M_AR01_Metal": 7.85, "M_AR01_Furniture": 0.65, "M_AR01_Mag": 7.85}     # g/cm^3


def log(*a):
    print("[AR01-game]", *a, flush=True)


def part_rec(ob):
    try:
        return json.loads(ob.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        return {}


def base_of(name):
    for lv in (1, 2, 3):
        sfx = f"_LOD{lv}"
        if name.endswith(sfx):
            return name[: -len(sfx)], lv
    return name, 0


def slot_of(o):
    rec = part_rec(o)
    if rec.get("slot"):
        return SLOT_INDEX[rec["slot"]]
    base, _ = base_of(o.name)
    return SLOT_INDEX[RS.SETS[RS.lod3_set(base)]["slot"]]


def clean_previous():
    for o in list(bpy.data.objects):
        if o.name.startswith((NAME, "UCX_" + NAME, "SOCKET_" + NAME)):
            bpy.data.objects.remove(o, do_unlink=True)
    c = bpy.data.collections.get(NAME)
    if c is not None:
        bpy.data.collections.remove(c)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)


def lod_objects(lv):
    cn = "AR01_Parts" if lv == 0 else f"AR01_LOD{lv}"
    return [o for o in bpy.data.collections[cn].objects if o.type == "MESH"]


def main():
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock as L
    L.assert_owner("AR01", "claude")
    t0 = time.time()
    clean_previous()
    for n in ("BAKE_Metal", "BAKE_Furniture", "BAKE_Mag", "BAKE_CheckerLow", "BAKE_CheckerHigh"):
        m = bpy.data.materials.get(n)
        if m is not None:
            bpy.data.materials.remove(m)
    mats = [GM.game_material(s, f"T_AR01_{s.split('_')[-1]}", TEX) for s in SLOTS]
    # the skeletal parts carry the game materials too (stage 5 binds them; their UV0 stays in 0..1)
    for lv in (0, 1, 2, 3):
        for o in lod_objects(lv):
            o.data.materials.clear()
            o.data.materials.append(mats[slot_of(o)])
    coll = bpy.data.collections.new(NAME)
    bpy.context.scene.collection.children.link(coll)
    lods = []
    report = {"lods": {}, "hulls": [], "sockets": {}}
    for lv in (0, 1, 2, 3):
        objs = lod_objects(lv)
        ob = GM.join_copies(objs, NAME if lv == 0 else f"{NAME}_LOD{lv}", coll, slot_of, mats, TILE)
        GM.uv1_from_uv0(ob, UV1_REGIONS)
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        mi = np.empty(len(ob.data.polygons), np.int32)
        ob.data.polygons.foreach_get("material_index", mi)
        report["lods"][f"LOD{lv}"] = {"triangles": tris, "rifle_triangles_without_mag": int((mi != 2).sum()),
                                      "mag_triangles": int((mi == 2).sum()), "parts": len(objs)}
        lods.append(ob)
        # per-part triangles for S2 / LOD-pop (frame M, mm)
        bl.export_npz(objs, OUT / f"lod{lv}_tris.npz", GRIP, [base_of(o.name)[0] for o in objs])
        log("LOD%d" % lv, tris, "tris")
    lod0 = lods[0]
    # ---------------------------------------------------------------- hulls
    samples = {}
    rng = np.random.default_rng(7)
    for lv in (0, 1, 2, 3):
        for o in lod_objects(lv):
            V, T = GM.mesh_vt(o)
            base = base_of(o.name)[0]
            pts = V if lv == 3 else GM.dense_samples(V, T, 1.0 if lv == 0 else 2.0)
            samples.setdefault(base, []).append(pts + GRIP)          # frame M
    samples = {k: np.vstack(v) for k, v in samples.items()}
    hulls = []
    for i, (desc, names, xr) in enumerate(HULLS):
        pts = [samples[n] for n in names if n in samples]
        if xr is not None:
            for n in LINE_PARTS:
                if n in samples:
                    s = samples[n]
                    m = np.ones(len(s), bool)
                    if xr[0] is not None:
                        m &= s[:, 0] >= xr[0]
                    if xr[1] is not None:
                        m &= s[:, 0] <= xr[1]
                    pts.append(s[m])
        if i == 0:                         # the receiver hull takes the line parts inside the receiver (X < 487)
            for n in LINE_PARTS:
                if n in samples:
                    s = samples[n]
                    pts.append(s[s[:, 0] <= 487.0])
        P = np.vstack(pts)
        h = GM.hull_from_points(f"UCX_{NAME}_{i:02d}", (P - GRIP) * 0.001, lod0, coll)
        hulls.append(h)
        report["hulls"].append({"name": h.name, "covers": desc, "vertices": len(h.data.vertices),
                                "points": int(len(P))})
        log("hull", h.name, len(h.data.vertices), "verts from", len(P), "points")
    # ---------------------------------------------------------------- mass properties (rifle without the magazine)
    m_tot, mc = 0.0, np.zeros(3)
    parts_g = {}
    for o in lod_objects(0):
        rec = part_rec(o)
        if rec.get("slot") == "M_AR01_Mag":
            continue
        vol, cen = GM.signed_volume_centroid(o)
        g = abs(vol) / 1000.0 * DENSITY[rec["slot"]]
        parts_g[o.name] = round(g, 1)
        m_tot += g
        mc += g * cen
    com_B = mc / m_tot                                      # frame B, mm
    report["mass"] = {"modelled_g": round(m_tot, 1), "com_B_mm": [round(float(v), 2) for v in com_B],
                      "spec_mass_kg_unloaded_without_mag": 3.1, "parts_g": parts_g,
                      "note": "hollow internals are not modelled: the physics mass is set to 3.1 kg (README); the CoM "
                              "is the modelled parts' (steel 7.85, wood 0.65 g/cm^3)"}
    log("mass", round(m_tot, 1), "g, CoM B", np.round(com_B, 2))
    # ---------------------------------------------------------------- sockets (spec, + computed CoM / Holster)
    for r in SPEC.sockets["rifle"]:
        name = r["socket"]
        loc = np.array(r["blender_mm"], float)
        if name in ("CenterOfMass", "Holster"):
            loc = com_B.copy()
        ro = r["unreal_rotation_deg"]
        eul = GM.blender_euler_for_ue(ro["roll"], ro["pitch"], ro["yaw"])
        so = make_socket(lod0, name, tuple(loc * 0.001), eul)
        report["sockets"][name] = {"blender_mm": [round(float(v), 4) for v in loc], "unreal_rotation_deg": ro,
                                   "bone": r["bone"], "computed": name in ("CenterOfMass", "Holster")}
    # ---------------------------------------------------------------- LOD group
    grp = make_lod_group(NAME, lods)
    grp["lod_screen_sizes"] = json.dumps(SCREEN_SIZES_START)
    for o in [grp] + list(grp.children_recursive):
        for c in list(o.users_collection):
            if c != coll:
                c.objects.unlink(o)
        if coll not in o.users_collection:
            coll.objects.link(o)
    V = np.array([v.co[:] for v in bpy.data.objects[f"{NAME}_LOD0"].data.vertices])
    half = 0.5 * np.linalg.norm(V.max(0) - V.min(0))
    Vr = np.array([v.co[:] for o in lod_objects(0) if part_rec(o).get("slot") != "M_AR01_Mag" for v in o.data.vertices])
    report["bounds_radius_m"] = {"twin_with_mag_box_half_diagonal": round(float(half), 4),
                                 "rifle_without_mag": round(float(0.5 * np.linalg.norm(Vr.max(0) - Vr.min(0))), 4)}
    report["names"] = {"group": grp.name, "lods": [o.name for o in lods], "hulls": [h.name for h in hulls],
                       "sockets": sorted(c.name for c in bpy.data.objects[f"{NAME}_LOD0"].children
                                         if c.name.startswith("SOCKET_"))}
    report["seconds"] = round(time.time() - t0, 1)
    (OUT / "game_report.json").write_text(json.dumps(report, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    log("GAME_DONE %.1fs" % (time.time() - t0))


main()
