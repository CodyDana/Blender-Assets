"""SR01 W3: the two static attachments, built and exported (headless Blender; the SMG's smg_mag.py, adapted):

    SR01_ATTACH=mag   blender -b Assets/Guns/SR01.blend --factory-startup --python Scripts/guns/sniper/sr_attach.py
    SR01_ATTACH=scope blender -b Assets/Guns/Att_Scope_LongRange.blend --factory-startup --python ...sr_attach.py

mag   SM_SR01_Mag from the gun's magazine parts at each LOD (the same LOD objects the twin merges; sr_game.py), origin
      = the Mag socket (seated pose: the gun's Mag socket and the magazine's coincide at zero relative transform);
      1 hull UCX_SM_SR01_Mag_LOD0_00; 5 sockets (spec sockets.mag); slot M_SR01_Mag; UV0 in 0..1.
scope SM_Att_Scope_LongRange from the surfaced scope parts (W2), origin = Mount (the rear ring's recoil lug on the
      rail-top plane); LOD1-2 by the same collapse decimation as the gun (sr_lodlib), 3 LODs; 3 hulls (eyepiece end,
      tube + turrets + rings, objective end); 5 sockets (Mount, Sight, EyePoint, Lens_Front, CenterOfMass); slots
      M_Att_Scope_Body (U tile 0) + M_Att_Scope_Lens (tile 1).
Both: qa_check before export_fbx(kind="static"); screen sizes = the gun twin's LOD-pop switch distances at the
attachment's own engine radius (it is seen with the gun); sha256 of the files. Writes scratch/w3/<mag|scope>/
<mag|scope>_report.json and saves the blend.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
KIND = os.environ.get("SR01_ATTACH", "mag")
if KIND == "scope":
    os.environ["SR01_SURFACE_TARGET"] = "scope"
from sr_common import ROOT, WORK, GRIP, GATES, CODE, PARTS_COLL, D, x_axis_rot  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import sr_surface as SS  # noqa: E402
import sr_lodlib as LL  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import ud as UD  # noqa: E402
from gunlib import tspace as TS  # noqa: E402
from gunlib import qa_gun  # noqa: E402
from pipeline.helpers import make_lod_group, make_socket  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402

EXPORTS = ROOT / "Exports" / "Guns" / CODE
TEX = EXPORTS / "Textures"
OUT = WORK / "scratch" / "w3" / KIND
OUT.mkdir(parents=True, exist_ok=True)
NAME = f"SM_{CODE}_Mag" if KIND == "mag" else "SM_Att_Scope_LongRange"


def log(*a):
    print(f"[SR01-{KIND}]", *a, flush=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def part_rec(ob):
    try:
        return json.loads(ob.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        return {}


def tris_of(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def clean_previous():
    for o in list(bpy.data.objects):
        if o.name.startswith((NAME, "UCX_" + NAME, "SOCKET_" + NAME)) or \
                (KIND == "scope" and any(o.name.endswith(f"_LOD{k}") for k in (1, 2)) and o.name.startswith("scope_")):
            d = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and getattr(d, "users", 1) == 0:
                bpy.data.meshes.remove(d)
    for cn in (NAME, "SCOPE_LOD1", "SCOPE_LOD2"):
        c = bpy.data.collections.get(cn)
        if c is not None:
            bpy.data.collections.remove(c)


def lod_parts():
    """[[objects of LOD k]] for the attachment."""
    if KIND == "mag":
        out = []
        for lv in range(4):
            cn = PARTS_COLL if lv == 0 else f"{CODE}_LOD{lv}"
            out.append([o for o in bpy.data.collections[cn].objects if o.type == "MESH"
                        and part_rec(o).get("slot") == "M_SR01_Mag"])
        return out
    parts0 = [o for o in bpy.data.collections[SS.SCOPE_COLL].objects if o.type == "MESH"]
    t0 = {o.name: tris_of(o) for o in parts0}
    out = [parts0]
    for lv, share, drop in ((1, 0.45, 0), (2, 0.15, 150)):
        coll = bpy.data.collections.new(f"SCOPE_LOD{lv}")
        bpy.context.scene.collection.children.link(coll)
        keep = [o for o in parts0 if t0[o.name] >= drop]
        ratio = min(1.0, share * sum(t0.values()) / sum(t0[o.name] for o in keep))
        objs = [LL.decimate_copy(o, f"{o.name}_LOD{lv}", coll, max(ratio, 16 / t0[o.name])) for o in keep]
        out.append(objs)
    return out


def main():
    from pipeline import lock as L
    L.assert_owner(CODE, "claude")
    t0 = time.time()
    clean_previous()
    rep = {"stage": f"W3 {NAME}", "lods": {}}
    if KIND == "mag":
        sets = ("Mag",)
        slot_names = ("M_SR01_Mag",)
        stem = f"T_{CODE}"
        origin_B = np.array([s for s in D["sockets"]["gun"] if s["socket"] == "Mag"][0]["B_mm"], float)
        sock_rows = [(s["socket"], np.array(s["mag_local_mm"], float)) for s in D["sockets"]["mag"]]
    else:
        sets = ("Scope_Body", "Scope_Lens")
        slot_names = tuple(SS.SETS[s]["slot"] for s in sets)
        stem = "T_Att_Scope_LongRange"
        origin_B = np.array(D["scope_attachment"]["mount_M"], float) - GRIP
        sock_rows = [(s["socket"], np.array(s["scope_local_mm"], float)) for s in D["sockets"]["scope"]]
    mats = [GM.game_material(sl, f"{stem}_{st}", TEX) for sl, st in zip(slot_names, sets)]
    tile = {i: (SS.TILE_OF_SET[s] if KIND == "scope" else 0.0) for i, s in enumerate(sets)}

    def slot_of(o):
        return slot_names.index(part_rec(o)["slot"]) if KIND == "mag" else \
            slot_names.index(json.loads(o.get("gun_part", "{}")).get("slot", slot_names[0]))
    L_parts = lod_parts()
    if KIND == "scope":
        for lv in (1, 2):
            fx = {st: LL.fix_uv_overlaps([o for o in L_parts[lv] if SS.SLOT_SET[part_rec(o)["slot"]] == st], "UV0")
                  for st in sets}
            fx["UV1"] = LL.fix_uv_overlaps(L_parts[lv], "UV1")
            import sr_uv                              # UD3: the W2 visible-sliver rule on the LOD parts (normals only)
            sr_uv.F32.clear()
            fx["ud3_visible_slivers"] = {k: v["corners_after"] for k, v in
                                         sr_uv.f32_visible({o.name: o for o in L_parts[lv]}).items()}
            rep.setdefault("uv_overlaps_collapsed", {})[f"LOD{lv}"] = fx
    coll = bpy.data.collections.new(NAME)
    bpy.context.scene.collection.children.link(coll)
    lods = []
    for lv, objs in enumerate(L_parts):
        ob = GM.join_copies(objs, NAME if lv == 0 else f"{NAME}_LOD{lv}", coll, slot_of, mats, tile)
        for lay in list(ob.data.uv_layers):
            if lay.name not in ("UV0", "UV1"):
                ob.data.uv_layers.remove(lay)
        ob.data.uv_layers.active = ob.data.uv_layers["UV0"]
        if lv:                                   # zero-area faces the decimation left (the FBX writer drops them)
            from gunlib import bl as _bl
            _bl.clean(ob, dist_m=1e-6)
            rep.setdefault("coincident_faces_removed", {})[f"LOD{lv}"] = LL.drop_coincident_pairs(ob)
        V = np.empty(len(ob.data.vertices) * 3)
        ob.data.vertices.foreach_get("co", V)
        V = V.reshape(-1, 3) - origin_B * 0.001                      # origin = Mag / Mount
        ob.data.vertices.foreach_set("co", V.ravel())
        ob.data.update()
        r = UD.check_object(ob)
        rep["lods"][f"LOD{lv}"] = {"triangles": tris_of(ob), "parts": [o.name for o in objs],
                                   "ud1_drops": int(r["unreal_drops"]), "min_area_mm2": r["min_area_mm2"],
                                   "ud3_zero": int(len(TS.float32_zero_corners(ob.data, "UV0")))}
        lods.append(ob)
        log(f"LOD{lv}", rep["lods"][f"LOD{lv}"])
    lod0 = lods[0]
    # ---------------------------------------------------------------- hulls (attachment-local mm)
    samples = []
    for ob in lods:
        V, T = GM.mesh_vt(ob)
        samples.append(GM.dense_samples(V, T, 1.0))
    P = np.vstack(samples)
    if KIND == "mag":
        groups = [("magazine body + floorplate", P)]
    else:
        x = P[:, 0]
        groups = [("eyepiece end + rear tube", P[x < -60.0 + 1.5]),
                  ("tube + turrets + focus + rings", P[(x >= -60.0 - 1.5) & (x < 160.0 + 1.5)]),
                  ("objective end", P[x >= 160.0 - 1.5])]
    rep["hulls"] = []
    for i, (desc, pts) in enumerate(groups):
        h = GM.hull_from_points(f"UCX_{NAME}_{i:02d}", pts * 0.001, lod0, coll)
        rep["hulls"].append({"name": h.name, "covers": desc, "vertices": len(h.data.vertices), "points": int(len(pts))})
    # ---------------------------------------------------------------- sockets
    com_local = None
    if KIND == "scope":
        vol_c = [GM.signed_volume_centroid(o) for o in L_parts[0]]
        vt = sum(abs(v) for v, _c in vol_c)
        com_local = sum(abs(v) * c for v, c in vol_c) / vt - origin_B
        rep["com_local_mm_volume"] = [round(float(v), 6) for v in com_local]
    rep["sockets"] = {}
    for name, loc in sock_rows:
        if name == "CenterOfMass" and com_local is not None:
            loc = com_local
        make_socket(lod0, name, tuple(loc * 0.001), (0.0, 0.0, 0.0))
        rep["sockets"][name] = {"location_mm": [round(float(v), 4) for v in loc], "unreal_rotation_deg": x_axis_rot((1, 0, 0))}
    grp = make_lod_group(NAME, lods)
    for o in [grp] + list(grp.children_recursive):
        for c in list(o.users_collection):
            if c != coll:
                c.objects.unlink(o)
        if coll not in o.users_collection:
            coll.objects.link(o)
    # ---------------------------------------------------------------- screen sizes: the gun's switch distances
    gz = json.loads((GATES / "game_lod_sizes.json").read_text())
    s_gun, r_gun = gz[f"SM_{CODE}"], float(gz["bounds_radius_m"])
    r_att = GM.static_sphere_radius(GM.mesh_vt(lod0)[0]) / 1000.0
    sizes = [1.0] + [round(s * r_att / r_gun, 5) for s in s_gun[1:len(lods)]]
    rep["screen_sizes"] = {"sizes": sizes, "engine_radius_m": round(r_att, 5), "gun_sizes": s_gun, "gun_radius_m": r_gun,
                           "rule": "the gun twin's LOD-pop switch distances (d = 1.778 r / s) at this attachment's own "
                                   "engine sphere radius"}
    grp["lod_screen_sizes"] = json.dumps(sizes)
    # ---------------------------------------------------------------- qa_check, export
    budget = int(D["budgets_triangles"]["mag_ceiling" if KIND == "mag" else "scope_ceiling"])
    q0 = qa_check(lods, budget_tris=budget, texel_density=None, require_uv1=True)
    agg = {c["object"]: float(c["detail"].split(" px/cm")[0]) for c in q0["checks"] if c["name"] == "texel_density"}
    q = qa_check(lods[:min(3, len(lods) - 1) or 1], budget_tris=budget, texel_density=agg[lods[0].name], require_uv1=True)
    rep["qa_check"] = {"passed": q0["passed"] and q["passed"], "triangles": q0["triangles"],
                       "texel_target_px_cm": agg[lods[0].name], "checks": len(q0["checks"]) + len(q["checks"]),
                       "failed": [c for c in q0["checks"] + q["checks"] if not c["passed"]]}
    log("qa_check", rep["qa_check"]["passed"], json.dumps(rep["qa_check"]["failed"])[:800])
    if not rep["qa_check"]["passed"]:
        (OUT / f"{KIND}_report.json").write_text(json.dumps(rep, indent=1, default=str))
        raise SystemExit(f"[SR01-{KIND}] qa_check failed: nothing exported")
    EXPORTS.mkdir(parents=True, exist_ok=True)
    res = export_fbx(str(EXPORTS / f"{NAME}.fbx"), [grp], kind="static", lod_screen_sizes=sizes)
    rep["export"] = {"fbx": res["filepath"], "sidecar": res["sidecar"], "warnings": res["warnings"],
                     "lod_screen_sizes": res["lod_screen_sizes"]}
    files = [res["filepath"], res["sidecar"]]
    rep["files"] = {str(Path(f).resolve().relative_to(ROOT.resolve())).replace("\\", "/"):
                    {"sha256": sha256(f), "bytes": Path(f).stat().st_size} for f in files}
    if KIND == "mag":
        # M7: the magazine is joined from the same LOD objects the shipped twin merged; record those twin bytes
        tw = [v for k, v in json.loads((WORK / "scratch" / "w3" / "rig" / "rig_report.json").read_text())["files"].items()
              if k.endswith("/SM_SR01.fbx")][0]
        rep["rifle_bytes"] = {"sha256": tw["sha256"], "file": "Exports/Guns/SR01/SM_SR01.fbx"}
    names = [NAME] + list(slot_names) + list(rep["sockets"]) + [h["name"] for h in rep["hulls"]] + [Path(f).name for f in files]
    rep["deny_tokens"] = {n: qa_gun.deny_hits(n) for n in names if qa_gun.deny_hits(n)}
    rep["seconds"] = round(time.time() - t0, 1)
    (OUT / f"{KIND}_report.json").write_text(json.dumps(rep, indent=1, default=str))
    bpy.ops.wm.save_mainfile()
    log("ATTACH_DONE", NAME, "%.1fs" % (time.time() - t0))


main()
