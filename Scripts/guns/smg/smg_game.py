"""SMG01 W3b: the static twin SM_SMG01 (headless Blender, after smg_lods.py; the AR-01's rifle_game.py):

    blender -b Assets/Guns/SMG01.blend --factory-startup --python Scripts/guns/smg/smg_game.py

- game materials M_SMG01_Metal (0), M_SMG01_Furniture (1), M_SMG01_Mag (2) on the painted maps
  (Exports/Guns/SMG01/Textures), set on every part object of every LOD (the rig binds the same objects);
- SM_SMG01_LOD0..3: each LOD's parts joined, the merged magazine included (Q10), stock EXTENDED; UV0 slot k on U tile k
  (Metal 0, Furniture 1, Mag -1; the parts keep every set in 0..1 for the skeletal mesh); UV1 = the authored lightmap of
  that LOD (smg_uv1 / smg_uv1lib: one 64 px atlas per LOD over all its parts, UD4 gated);
- 8 hulls UCX_SM_SMG01_LOD0_00..07 (spec collision.twin / plan 11) from dense surface samples of every LOD (LOD0
  <= 1 mm, LOD1-2 <= 2 mm, LOD3 vertices), the parts split by region where one moulding spans two hulls (the lower
  receiver: housing / grip + guard / magwell; the upper: body / fore-end below the bore; the barrel: inside / exposed),
  neighbours overlapping 3 mm, <= 32 vertices, dilated 0.2 mm, grown until every sample is inside;
- 21 sockets (spec sockets.gun; CenterOfMass from the LOD0 part volumes x densities, stock extended, magazine out;
  Holster = CenterOfMass) as Empties on LOD0 (pipeline.helpers.make_socket);
- the LOD group with the start screen sizes (the LOD-pop gate fixes them: smg_viewgates / game_lod_sizes.json).
Writes scratch/game/game_report.json and scratch/game/lod<k>_tris.npz + lod<k>_folded_tris.npz (per-part labels, frame
M, mm: the LOD-pop gate on both stock states, S2) and saves Assets/Guns/SMG01.blend.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, SCRATCH, BLEND, GRIP, SPEC, CODE, PARTS_COLL, BORE_Z, dims, D  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import smg_surface as SS  # noqa: E402
from gunlib import game as GM  # noqa: E402
from pipeline.helpers import make_lod_group, make_socket  # noqa: E402

NAME = f"SM_{CODE}"
OUT = SCRATCH / "game"
OUT.mkdir(parents=True, exist_ok=True)
TEX = ROOT / "Exports" / "Guns" / CODE / "Textures"
SETS = ("Metal", "Furniture", "Mag")
SLOTS = tuple(SS.SETS[s]["slot"] for s in SETS)
SLOT_INDEX = {s: i for i, s in enumerate(SLOTS)}
TILE = {i: SS.TILE_OF_SET[s] for i, s in enumerate(SETS)}
SCREEN_SIZES_START = [float(v) for v in D["lods"]["gun_screen_sizes_start"]]
MASS_KG = float(D["scale"]["mass_kg"])
DENSITY = {"M_SMG01_Metal": 7.85, "M_SMG01_Furniture": 1.4, "M_SMG01_Mag": 1.4}   # g/cm3 (spec collision.physics_asset)
SH = dims("stock_hinge")
FOLD_AXIS_M = np.array([float(SH["axis_X"]), float(SH["axis_Y"]), 0.0])
FOLD_DEG = float(SH["fold_rot_Z_deg"])

# stations (frame M) for the hull regions
ST = D["stations_X"]
X_MW_REAR, X_MW_FRONT = float(SPEC.box("magwell")["X"][0]), float(ST["magwell_front_face"])
X_FRONT_FACE = float(ST["receiver_front_face"])
Z_HOUSING_BOT = float(SPEC.box("lower_receiver")["Z"][0])          # -50.3: the trigger housing's bottom
OV = 1.5                                                            # each side of a split: 3 mm overlap


def log(*a):
    print("[SMG01-game]", *a, flush=True)


def part_rec(ob):
    try:
        return json.loads(ob.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        return {}


def base_of(name):
    for lv in (1, 2, 3):
        if name.endswith(f"_LOD{lv}"):
            return name[: -len(f"_LOD{lv}")], lv
    return name, 0


def slot_of(o):
    return SLOT_INDEX[part_rec(o)["slot"]]


def lod_objects(lv):
    cn = PARTS_COLL if lv == 0 else f"{CODE}_LOD{lv}"
    return [o for o in bpy.data.collections[cn].objects if o.type == "MESH"]


def clean_previous():
    for o in list(bpy.data.objects):
        if o.name.startswith((NAME, "UCX_" + NAME, "SOCKET_" + NAME)) and not o.name.startswith(NAME + "_Mag"):
            d = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and getattr(d, "users", 1) == 0:
                bpy.data.meshes.remove(d)
    c = bpy.data.collections.get(NAME)
    if c is not None:
        bpy.data.collections.remove(c)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)


def fold_matrix_M():
    """Frame-M 4x4: the stock folded (rotation about the hinge axle, Z)."""
    a = math.radians(FOLD_DEG)
    R = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = FOLD_AXIS_M - R @ FOLD_AXIS_M
    return M


def export_lod_npz(objs, path, folded=False):
    """bl.export_npz's format (V mm frame M, T, lab, names = base part names); folded: the stock-bone parts turned
    about the hinge axle."""
    from gunlib import bl
    Mf = fold_matrix_M()
    Vs, Ts, Ls, names = [], [], [], []
    n = 0
    for k, ob in enumerate(objs):
        V, T = bl.tris_np(ob, GRIP)
        if folded and part_rec(ob).get("bone") == "stock":
            V = V @ Mf[:3, :3].T + Mf[:3, 3]
        Vs.append(V)
        Ts.append(T + n)
        Ls.append(np.full(len(T), k, np.int32))
        names.append(base_of(ob.name)[0])
        n += len(V)
    np.savez_compressed(path, V=np.vstack(Vs), T=np.vstack(Ts), lab=np.concatenate(Ls), names=np.array(names))


# ---------------------------------------------------------------------------------- hulls (plan 11 / spec)
def _lower_region(P):
    x, z = P[:, 0], P[:, 2]
    return {"housing": (z >= Z_HOUSING_BOT - OV) & (x <= X_MW_REAR + OV),
            "grip_guard": (z < Z_HOUSING_BOT + OV) & (x < X_MW_REAR + OV),
            "magwell": x >= X_MW_REAR - OV}


def hull_points(samples):
    """samples: {base part name: points (frame M)} -> [(name, covers, points)] for the 8 hulls."""
    def take(names):
        return [samples[n] for n in names if n in samples]

    def sel(name, key):
        if name not in samples:
            return []
        P = samples[name]
        return [P[_lower_region(P)[key]]]
    up = samples.get("upper_receiver")
    up_body = [up[(up[:, 0] <= X_MW_FRONT + OV) | (up[:, 2] >= BORE_Z - OV)]] if up is not None else []
    up_fore = [up[(up[:, 0] >= X_MW_FRONT - OV) & (up[:, 2] <= BORE_Z + OV)]] if up is not None else []
    br = samples.get("barrel")
    br_in = [br[br[:, 0] <= X_FRONT_FACE + OV]] if br is not None else []
    br_out = [br[br[:, 0] >= X_FRONT_FACE - OV]] if br is not None else []
    # LOD3 silhouette volumes carry their own names (smg_blockout): fold them into the same groups
    groups = [
        ("receiver body + top rail (end block, bolt, charging handle, selector, pins)",
         up_body + sel("lower_receiver", "housing") + br_in +
         take(("top_rail", "rail_screws", "bolt", "bolt_rails", "charging_handle", "charging_slide", "selector",
               "pins_fasteners", "trigger_axle", "mag_release_pin", "upper_fore_end", "end_block"))),
        ("rear flip sight", take(("sight_rear_base", "sight_rear_leaf", "sight_rear_pin", "sight_rear"))),
        ("front flip sight", take(("sight_front_base", "sight_front_leaf", "sight_front_pin", "sight_front"))),
        ("fore-end below the bore + lower rail", up_fore + take(("lower_rail",))),
        ("barrel (exposed) + muzzle device", br_out + take(("muzzle_device",))),
        ("grip + trigger guard (trigger, paddle, grip cover)",
         sel("lower_receiver", "grip_guard") + take(("grip_cover", "trigger", "mag_release", "trigger_guard",
                                                     "pistol_grip"))),
        ("merged magazine + magwell (twin only)",
         sel("lower_receiver", "magwell") + take(("magazine", "magazine_follower", "magazine_floor_plate", "magwell"))),
        ("stock frame + buttpad (extended; latch, axle)",
         take(("stock_frame", "butt_pad", "stock_latch_button", "stock_latch_bolt", "hinge_axle", "stock_hinge",
               "stock_neck", "stock_top_strut", "stock_lower_strut", "stock_web", "stock_rear_upright"))),
    ]
    return groups


def main():
    from pipeline import lock as L
    L.assert_owner(CODE, "claude")
    t0 = time.time()
    clean_previous()
    for n in [m.name for m in bpy.data.materials if m.name.startswith("BAKE_")]:
        bpy.data.materials.remove(bpy.data.materials[n])
    mats = [GM.game_material(s, f"T_{CODE}_{st}", TEX) for s, st in zip(SLOTS, SETS)]
    for lv in range(4):
        for o in lod_objects(lv):
            o.data.materials.clear()
            o.data.materials.append(mats[slot_of(o)])
    coll = bpy.data.collections.new(NAME)
    bpy.context.scene.collection.children.link(coll)
    rep = {"stage": "W3b game: static twin, hulls, sockets", "lods": {}, "hulls": [], "sockets": {}}
    lods = []
    for lv in range(4):
        objs = lod_objects(lv)
        ob = GM.join_copies(objs, NAME if lv == 0 else f"{NAME}_LOD{lv}", coll, slot_of, mats, TILE)
        for lay in list(ob.data.uv_layers):
            if lay.name not in ("UV0", "UV1"):
                ob.data.uv_layers.remove(lay)
        ob.data.uv_layers.active = ob.data.uv_layers["UV0"]
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        mi = np.empty(len(ob.data.polygons), np.int32)
        ob.data.polygons.foreach_get("material_index", mi)
        rep["lods"][f"LOD{lv}"] = {"triangles": tris, "gun_triangles_without_mag": int((mi != 2).sum()),
                                   "mag_triangles": int((mi == 2).sum()), "parts": len(objs),
                                   "uv_layers": [l.name for l in ob.data.uv_layers]}
        lods.append(ob)
        export_lod_npz(objs, OUT / f"lod{lv}_tris.npz")
        export_lod_npz(objs, OUT / f"lod{lv}_folded_tris.npz", folded=True)
        log("LOD%d" % lv, tris, "tris")
    lod0 = lods[0]
    # ---------------------------------------------------------------- hulls
    samples = {}
    for lv in range(4):
        for o in lod_objects(lv):
            V, T = GM.mesh_vt(o)
            pts = V if lv == 3 else GM.dense_samples(V, T, 1.0 if lv == 0 else 2.0)
            samples.setdefault(base_of(o.name)[0], []).append(pts + GRIP)
    samples = {k: np.vstack(v) for k, v in samples.items()}
    hulls = []
    for i, (desc, pts) in enumerate(hull_points(samples)):
        P = np.vstack([p for p in pts if len(p)])
        h = GM.hull_from_points(f"UCX_{NAME}_{i:02d}", (P - GRIP) * 0.001, lod0, coll)
        hulls.append(h)
        rep["hulls"].append({"name": h.name, "covers": desc, "vertices": len(h.data.vertices), "points": int(len(P))})
        log("hull", h.name, len(h.data.vertices), "verts from", len(P), "points")
    # ---------------------------------------------------------------- mass properties (stock extended, magazine out)
    from gunlib.game import signed_volume_centroid
    Mf = fold_matrix_M()
    m_tot, mc, mcf = 0.0, np.zeros(3), np.zeros(3)
    parts_g = {}
    for o in lod_objects(0):
        rec = part_rec(o)
        if rec.get("slot") == "M_SMG01_Mag":
            continue
        vol, cen = signed_volume_centroid(o)
        g = abs(vol) / 1000.0 * DENSITY[rec["slot"]]
        parts_g[o.name] = round(g, 1)
        m_tot += g
        mc += g * cen
        cM = cen + GRIP
        cf = (Mf[:3, :3] @ cM + Mf[:3, 3]) - GRIP if rec.get("bone") == "stock" else cen
        mcf += g * cf
    com_B = mc / m_tot
    com_fold_B = mcf / m_tot
    rep["mass"] = {"modelled_g": round(m_tot, 1), "mass_kg": MASS_KG, "com_B_mm": [round(float(v), 2) for v in com_B],
                   "com_folded_B_mm": [round(float(v), 2) for v in com_fold_B], "parts_g": parts_g,
                   "densities_g_cm3": DENSITY,
                   "note": "part volumes x densities (glass-filled polymer 1.4, steel 7.85; spec collision.physics_asset), "
                           "the total scaled to the spec's 2.5 kg (the CoM is the modelled parts'; hollow internals are "
                           "not modelled): stock extended, magazine out; the folded CoM is reported"}
    log("mass", round(m_tot, 1), "g modelled, CoM B", np.round(com_B, 2), "folded", np.round(com_fold_B, 2))
    # ---------------------------------------------------------------- sockets
    for r in SPEC.gun_sockets():
        name = r["socket"]
        loc = np.array(r["blender_mm"], float)
        if name in ("CenterOfMass", "Holster"):
            loc = com_B.copy()
        ro = r["unreal_rotation_deg"]
        eul = GM.blender_euler_for_ue(ro["roll"], ro["pitch"], ro["yaw"])
        make_socket(lod0, name, tuple(loc * 0.001), eul)
        rep["sockets"][name] = {"blender_mm": [round(float(v), 4) for v in loc], "unreal_rotation_deg": ro,
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

    def half_diag(V):
        return round(float(0.5 * np.linalg.norm(V.max(0) - V.min(0))) / 1000.0, 4)
    V0 = GM.mesh_vt(bpy.data.objects[f"{NAME}_LOD0"])[0]
    Vg = np.vstack([GM.mesh_vt(o)[0] for o in lod_objects(0) if part_rec(o).get("slot") != "M_SMG01_Mag"])
    stock = np.array([part_rec(o).get("bone") == "stock" for o in lod_objects(0)
                      if part_rec(o).get("slot") != "M_SMG01_Mag"])
    Vfold = []
    for o in lod_objects(0):
        if part_rec(o).get("slot") == "M_SMG01_Mag":
            continue
        V = GM.mesh_vt(o)[0]
        if part_rec(o).get("bone") == "stock":
            V = ((V + GRIP) @ Mf[:3, :3].T + Mf[:3, 3]) - GRIP
        Vfold.append(V)
    Vfold = np.vstack(Vfold)
    # (W4 review fixes) the twin's LOD sizes convert at Unreal's static-mesh sphere radius (max |v - box centre|,
    # gunlib.game.static_sphere_radius; the AR-01's engine numbers confirm the rule), not the box half-diagonal: W3's
    # half-diagonal (0.3508) put the twin's switches 6.4 % closer than the LOD-pop distances
    rep["bounds_radius_m"] = {"twin_engine_sphere_radius": round(GM.static_sphere_radius(V0) / 1000.0, 5),
                              "twin_with_mag_box_half_diagonal": half_diag(V0), "gun_without_mag": half_diag(Vg),
                              "gun_folded_without_mag": half_diag(Vfold),
                              "spec": D["lods"]["bounds_radius_m"]}
    rep["names"] = {"group": grp.name, "lods": [o.name for o in lods], "hulls": [h.name for h in hulls],
                    "sockets": sorted(c.name for c in bpy.data.objects[f"{NAME}_LOD0"].children
                                      if c.name.startswith("SOCKET_"))}
    rep["seconds"] = round(time.time() - t0, 1)
    (OUT / "game_report.json").write_text(json.dumps(rep, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    log("GAME_DONE %.1fs" % (time.time() - t0))


main()
