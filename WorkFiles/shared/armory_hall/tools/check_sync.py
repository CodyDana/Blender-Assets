"""The SYNC.md section-8 checks for either side, plain Python 3 (no Unreal, no Blender). Run it at the start of every
armory or hall session and after every change, from the repo root:

    py -3 -B WorkFiles/shared/armory_hall/tools/check_sync.py --side dojo       # the dojo chat (DojoLab)
    py -3 -B WorkFiles/shared/armory_hall/tools/check_sync.py --side armory     # the armory chat (ArmoryLab)
    [--json <report.json>] [--quiet]

Exit codes:  0 = every check passes and your project is synced (at or after manifest.sync_needed_rev[<project>])
             2 = every check passes but your project is behind: run your sync, then record it
             3 = a generated shared file is stale against its owner's build data: interior_layout.json /
                 lights_design.json (the armory chat: tools/regen_interior.py --write, bump), or, on the dojo side only,
                 shell_materials.json / shell_masters.json (the dojo chat: make_shell_materials.py --write /
                 tools/master_snapshot.py --write, bump)
             1 = a check failed: fix it before any other work (the message says which file / who owes what)

Checks:
  files     every shared file's sha256 equals manifest.shared_files (an edit without a bump is caught)
  sha       every FBX (interior, shell, items; DojoLab-only site pieces on the dojo side), texture PNG and material
            .uasset equals manifest.json: ArmoryLab's own packages (the armory's source) on both sides; DojoLab's
            byte copies on the dojo side (a copy that differs = sync needed); shell_materials.json's FBX / PNG
  pieces    every instance's piece is listed in the manifest and its FBX exists; ids unique; no retired id reused
  envelope  MESH LEVEL on the exported FBX bytes (tools/fbxlite.py; render meshes, LODs and UCX hulls):
            every interior vertex and design light inside interface.json envelope.with_walls (0.012 m); every
            placed shell vertex outside it except inside envelope.shell_intrusions; each interior instance's layout
            bbox within 2 cm of its FBX (SYNC.md 9: otherwise the piece needs a new name)
  names     every name ever listed is still listed or retired; every used name is listed
  lights    shadowed local lights <= the side's budget (ArmoryLab: shadow_policy.armorylab_budget; DojoLab:
            Scripts/dojo/unreal/dj_armory_look.py SHADOW_BUDGET with its SHADOW_OFF_ROLES)
  fresh     the interior jsons equal what tools/regen_interior.py builds from the armory's data now; on the dojo side
            shell_materials.json equals Scripts/dojo/hall/make_shell_materials.py's output
  masters   (rev 4) the shell masters' live graph code (tools/master_snapshot.py over Scripts/dojo/unreal/
            dj_sc_materials.py + dj_sc_common.py + layout_showcase.json) equals shell_masters.json and the manifest's
            shell_master_graph: dojo side stale (3: snapshot + bump owed), armory side FAIL (1: never build the shell
            from an unrevisioned master graph)
  hall_variant  (rev 4, armory side, once ArmoryLab has synced) WorkFiles/armory/build/unreal/armory_hall_sync/shell.json
            is a passed, non-test run at the recorded revision with the counts the shared files give now, and the
            armory's level.json is not newer than shell.json (ak_level.py after the tool = L_Armory is no longer the
            hall variant: re-run the tool, SYNC.md 3); any miss = behind (2)
  revision  the revision your project last synced (dojo: WorkFiles/dojo/build/unreal/armory_sync/synced_revision.json;
            armory: WorkFiles/armory/build/unreal/armory_hall_sync/synced_revision.json, else the line
            'armory_hall synced rev N' in WorkFiles/armory/build/BUILD_NOTES.md) against manifest.sync_needed_rev[project]
            (the last revision that changed what that project's Unreal sync reads; before rev 4: the revision)
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ahcommon as A  # noqa: E402

RES = {"fail": [], "stale": [], "behind": [], "warn": [], "info": {}}


def fail(msg):
    RES["fail"].append(msg)


def check_files(M):
    rec = M.get("shared_files")
    if not rec:
        fail("manifest.shared_files missing: bump the manifest once with tools/bump_manifest.py")
        return
    for n in A.SHARED_FILES:
        p = A.SH / n
        if not p.exists():
            fail(f"files: {n} is missing")
        elif rec.get(n) != A.sha256(p):
            fail(f"files: {n} changed after revision {M['revision']} without a manifest bump (bump_manifest.py)")


def check_sha(M, S, side):
    n = 0
    for name, r in M["fbx"].items():
        f = A.ROOT / r["path"]
        n += 1
        if not f.exists():
            fail(f"sha: {r['path']} missing")
        elif A.sha256(f) != r["sha256"]:
            owner = "the armory chat" if r.get("owner") == "armory" else "the dojo chat"
            fail(f"sha: {r['path']} differs from manifest rev {M['revision']} ({owner} owes a bump or a re-export)")
        sc = f.with_suffix(".sockets.json")
        if r.get("sidecar_sha256") and sc.exists() and A.sha256(sc) != r["sidecar_sha256"]:
            fail(f"sha: {A.rel(sc)} differs from the manifest")
    for name, r in M.get("item_fbx", {}).items():
        n += 1
        f = A.ROOT / r["path"]
        if not f.exists() or A.sha256(f) != r["sha256"]:
            fail(f"sha: item {r['path']} missing or differs from the manifest")
    for t, r in M.get("textures", {}).items():
        n += 1
        if r.get("png") and A.sha256(A.ROOT / r["png"]) != r["png_sha256"]:
            fail(f"sha: {r['png']} differs from the manifest")
        ua = A.ARMORYLAB / "Content/ArmoryKit/Textures" / f"{t}.uasset"
        if r.get("armorylab_uasset_sha256"):
            if not ua.exists() or A.sha256(ua) != r["armorylab_uasset_sha256"]:
                fail(f"sha: ArmoryLab texture {t}.uasset differs from the manifest (the armory chat owes a bump)")
            if side == "dojo":
                cp = A.DOJOLAB / "Content/ArmoryKit/Textures" / f"{t}.uasset"
                if not cp.exists() or A.sha256(cp) != r["armorylab_uasset_sha256"]:
                    RES["behind"].append(f"DojoLab copy of texture {t} differs from the manifest (run the sync)")
    for m, r in M["materials"]["assets"].items():
        n += 1
        ua = A.ARMORYLAB / "Content/ArmoryKit/Materials" / f"{m}.uasset"
        if not ua.exists() or A.sha256(ua) != r["sha256"]:
            fail(f"sha: ArmoryLab material {m}.uasset differs from the manifest (the armory chat owes a bump)")
        if side == "dojo":
            cp = A.DOJOLAB / "Content/ArmoryKit/Materials" / f"{m}.uasset"
            if not cp.exists() or A.sha256(cp) != r["sha256"]:
                RES["behind"].append(f"DojoLab copy of material {m} differs from the manifest (run the sync)")
    for t, r in M.get("shell_textures", {}).items():
        n += 1
        if A.sha256(A.ROOT / r["png"]) != r["sha256"]:
            fail(f"sha: shell texture {r['png']} differs from the manifest (the dojo chat owes a bump)")
    SM = S.get("shell_materials")
    if SM:
        for p, r in SM["pieces"].items():
            if M["fbx"].get(p, {}).get("sha256") != r["sha256"]:
                fail(f"sha: shell_materials.json {p} sha differs from the manifest")
    if side == "dojo":
        for k, r in M.get("site_fbx_dojolab_only", {}).items():
            n += 1
            f = A.ROOT / r["path"]
            if not f.exists() or A.sha256(f) != r["sha256"]:
                fail(f"sha: DojoLab-only {r['path']} differs from the manifest")
    RES["info"]["sha_entries_checked"] = n


def check_pieces(M, S):
    I, H = S["interior_layout"], S["hall_shell_layout"]
    ids = [i["id"] for i in I["instances"]]
    if len(ids) != len(set(ids)):
        fail("pieces: duplicate AKI ids")
    ret = {r["id"] for r in I.get("retired_ids", [])}
    if ret & set(ids):
        fail(f"pieces: retired ids reused {sorted(ret & set(ids))[:5]}")
    for it in I["instances"]:
        if it["piece"] not in I["pieces"] or it["piece"] not in M["fbx"]:
            fail(f"pieces: {it['id']} uses {it['piece']}, which is not listed")
    sids = [i["id"] for i in H["instances_existing"] + H["instances_new"]]
    if len(sids) != len(set(sids)):
        fail("pieces: duplicate shell ids")
    for i in A.placed_shell(H):
        if i["piece"] not in M["fbx"]:
            fail(f"pieces: shell {i['id']} uses {i['piece']}, which is not listed")
    RES["info"]["interior_instances"] = len(ids)
    RES["info"]["shell_instances_placed"] = len(A.placed_shell(H))


def check_envelope(S):
    I, H, F, D = S["interior_layout"], S["hall_shell_layout"], S["interface"], S["lights_design"]
    ww = F["envelope"]["with_walls"]
    lo = np.array([ww["x"][0], ww["y"][0], ww["z"][0]])
    hi = np.array([ww["x"][1], ww["y"][1], ww["z"][1]])
    tol = A.TOL
    worst_out, bbox_err, n_v = 0.0, [], 0
    for it in I["instances"]:
        ms = A.fbx_meshes(A.EXPORTS_AK / f"{it['piece']}.fbx")
        v = A.rotz(np.vstack(list(ms.values())), float(it["rot_z_deg"])) + np.array(it["loc_m"])
        n_v += len(v)
        out = np.maximum(lo - v, v - hi).max()
        worst_out = max(worst_out, float(out))
        if out > tol:
            fail(f"envelope: interior {it['id']} {it['piece']} pokes {out:.3f} m out of envelope.with_walls")
        e = float(np.abs(np.concatenate([v.min(0), v.max(0)]) - np.array(it["bbox_m"])).max())
        if e > 0.02:
            bbox_err.append((it["id"], it["piece"], round(e, 4)))
    for (iid, p, e) in bbox_err[:10]:
        fail(f"envelope: {iid} {p}: the FBX differs from the layout bbox by {e} m (> 2 cm: SYNC.md 9 needs a new name, "
             f"or regen_interior.py was not run after the re-export)")
    for L in D["lights"]:
        p = np.array(L["loc_m"])
        if (p < lo - tol).any() or (p > hi + tol).any():
            fail(f"envelope: design light {L['name']} outside the envelope")
    boxes = A.intrusion_boxes(F)
    bad, n_s, low_over = {}, 0, None
    for i in A.placed_shell(H):
        ms = A.fbx_meshes(A.EXPORTS_HALL / f"{i['piece']}.fbx")
        v = A.rotz(np.vstack(list(ms.values())), float(i["rot_z_deg"])) + np.array(i["loc_world_m"]) - np.array(A.HALL_TO_DOJO)
        n_s += len(v)
        ins = ((v > lo + tol) & (v < hi - tol)).all(1)
        ok = np.zeros(len(v), bool)
        for _w, bx, by, bz in boxes:
            b0 = np.array([bx[0], by[0], bz[0]]) - tol
            b1 = np.array([bx[1], by[1], bz[1]]) + tol
            ok |= ((v >= b0) & (v <= b1)).all(1)
        k = int((ins & ~ok).sum())
        if k:
            bad[i["id"]] = (i["piece"], k)
        over = (v[:, 0] > lo[0]) & (v[:, 0] < hi[0]) & (v[:, 1] > lo[1]) & (v[:, 1] < hi[1]) & (v[:, 2] >= hi[2] - tol)
        if over.any():
            m = float(v[over, 2].min())
            low_over = m if low_over is None else min(low_over, m)
    for sid, (p, k) in bad.items():
        fail(f"envelope: shell {sid} {p} has {k} vertices inside the interior envelope outside the shell intrusions")
    RES["info"]["envelope"] = {"interior_vertices": n_v, "interior_worst_out_m": round(worst_out, 4),
                               "interior_bbox_gt_2cm": len(bbox_err), "shell_vertices": n_s,
                               "shell_vertices_inside": int(sum(k for _p, k in bad.values())),
                               "lowest_shell_vertex_over_the_envelope_plan_m": None if low_over is None else round(low_over, 4)}


def check_names(M, S):
    ever = set(M.get("names_ever") or [])
    if not ever:
        RES["warn"].append("names: manifest.names_ever not recorded yet (written by the next bump)")
    retired = {r["name"] if isinstance(r, dict) else r for r in M.get("retired", [])}
    gone = sorted(n for n in ever if n not in M["fbx"] and n not in retired)
    if gone:
        fail(f"names: listed names disappeared without being retired: {gone}")
    used = set(S["interior_layout"]["pieces"]) | {i["piece"] for i in A.placed_shell(S["hall_shell_layout"])}
    if used & retired:
        fail(f"names: retired names in use again: {sorted(used & retired)}")


def check_lights(S, side):
    D = S["lights_design"]
    if side == "armory":
        n = sum(1 for L in D["lights"] if L.get("ue_armorylab_night", {}).get("shadows"))
        budget = int(D["shadow_policy"].get("armorylab_budget", 12))
    else:
        sys.path.insert(0, str(A.ROOT / "Scripts/dojo/unreal"))
        import dj_armory_look as LOOK  # noqa: PLC0415
        n = sum(1 for L in D["lights"] if L.get("ue_armorylab_night", {}).get("shadows")
                and L["role"] not in LOOK.SHADOW_OFF_ROLES)
        budget = int(LOOK.SHADOW_BUDGET)
    RES["info"]["shadowed_local_lights"] = {"n": n, "budget": budget}
    if n > budget:
        fail(f"lights: {n} shadowed local lights > the {side} budget {budget}")


def check_fresh(S, side):
    try:
        import regen_interior as R  # noqa: PLC0415
        I, D, viol, _idrep, _v = R.build(S["interior_layout"], S["lights_design"], S["interface"])
        dI, dD = R.diff(S["interior_layout"], I), R.diff(S["lights_design"], D)
        RES["info"]["fresh_interior"] = {"interior_layout_changes": len(dI), "lights_design_changes": len(dD),
                                         "envelope_violations_in_armory_data": len(viol)}
        if dI or dD:
            RES["stale"].append(f"fresh: the armory's build data differs from interior_layout.json ({len(dI)}) / "
                                f"lights_design.json ({len(dD)}): the armory chat runs tools/regen_interior.py --write "
                                f"and bumps (first lines: {(dI + dD)[:3]})")
        if viol:
            fail(f"fresh: the armory's current build data has {len(viol)} envelope violation(s): {viol[:2]}")
    except FileNotFoundError as exc:
        RES["warn"].append(f"fresh: armory build data not readable ({exc}); skipped")
    if side == "dojo":
        r = subprocess.run([sys.executable, "-B", str(A.ROOT / "Scripts/dojo/hall/make_shell_materials.py")],
                           capture_output=True, text=True, cwd=str(A.ROOT))
        RES["info"]["fresh_shell_materials"] = r.stdout.strip().splitlines()[-1:] if r.stdout else r.stderr[-300:]
        if r.returncode == 4:
            RES["stale"].append("fresh: shell_materials.json differs from the dojo build data: "
                                "py -3 -B Scripts/dojo/hall/make_shell_materials.py --write, then bump")
        elif r.returncode != 0:
            fail(f"fresh: make_shell_materials.py failed: {r.stdout[-300:]} {r.stderr[-300:]}")


def check_masters(M, side):
    import master_snapshot as MS  # noqa: PLC0415
    live = MS.build()
    snap = A.jload(MS.OUT) if MS.OUT.exists() else None
    rec = (M.get("shell_master_graph") or {}).get("graph_sha256")
    RES["info"]["shell_master_graph"] = {"live": live["graph_sha256"][:16], "snapshot": (snap or {}).get("graph_sha256", "")[:16],
                                         "manifest": (rec or "")[:16]}
    d = MS.diff(snap, live)
    if d:
        msg = (f"masters: the shell masters' graph code (Scripts/dojo/unreal/dj_sc_materials.py / dj_sc_common.py / "
               f"layout_showcase.json) differs from shell_masters.json ({'; '.join(d[:4])})")
        if side == "dojo":
            RES["stale"].append(msg + ": py -3 -B WorkFiles/shared/armory_hall/tools/master_snapshot.py --write, then bump")
        else:
            fail(msg + ": the dojo chat owes master_snapshot.py --write + a bump; do not sync ArmoryLab until then")
    elif rec and snap and rec != snap.get("graph_sha256"):
        fail("masters: shell_masters.json differs from manifest.shell_master_graph (the dojo chat owes a bump)")
    elif not rec:
        RES["warn"].append("masters: manifest.shell_master_graph not recorded yet (written by the next bump)")


def check_hall_variant(S, side):
    """Armory side: the ArmoryLab sync ended with tools/ue_armorylab_shell.py and nothing rebuilt the level after it."""
    if side != "armory":
        return
    d = A.ARMORY_BUILD / "unreal" / "armory_hall_sync"
    rec_f, shell_f, level_f = d / "synced_revision.json", d / "shell.json", A.ARMORY_BUILD / "unreal" / "level.json"
    if not rec_f.exists():
        return      # never synced: the revision check reports behind
    if not shell_f.exists():
        RES["behind"].append("hall_variant: synced_revision.json without shell.json: run tools/ue_armorylab_shell.py (SYNC.md 3)")
        return
    R, I, H = A.jload(shell_f), S["interior_layout"], S["hall_shell_layout"]
    want = {"shell_placed": len(A.placed_shell(H)),
            "exterior_hidden": len(I["not_used_in_the_hall"]["instances"]),
            "substitution_tiles": sum(1 for it in I["instances"] if it.get("src_armory", {}).get("layout_index") is None),
            "lifted": sum(1 for it in I["instances"] if it.get("z_shift_m") and it.get("src_armory", {}).get("layout_index")
                          is not None) + sum(1 for L in S["lights_design"]["lights"] if L.get("z_shift_m"))}
    hv, eh = R.get("hall_variant", {}), R.get("exterior_hidden", {})
    got = {"shell_placed": R.get("shell_placed"), "exterior_hidden": eh.get("found") if eh.get("found") == eh.get("want") else None,
           "substitution_tiles": hv.get("substitution_tiles"), "lifted": hv.get("lifted")}
    bad = [f"{k} {got[k]} (want {v})" for k, v in want.items() if got[k] != v]
    if R.get("test") or not R.get("passed"):
        bad.append(f"passed={R.get('passed')} test={R.get('test')}")
    if (R.get("bounds_gate") or {}).get("max_bounds_err_cm", 99.0) > 1.0:
        bad.append(f"bounds {R.get('bounds_gate', {}).get('max_bounds_err_cm')} cm > 1")
    if hv.get("lifted_missing"):
        bad.append(f"lifted_missing {hv['lifted_missing'][:5]}")
    if R.get("manifest_revision") != A.jload(rec_f).get("ArmoryLab"):
        bad.append(f"shell.json rev {R.get('manifest_revision')} != synced_revision.json")
    if level_f.exists() and level_f.stat().st_mtime > shell_f.stat().st_mtime:
        bad.append("ak_level.py rebuilt L_Armory after the tool (level.json newer than shell.json): L_Armory is no longer "
                   "the hall variant")
    RES["info"]["hall_variant"] = {"want": want, "got": got, "ok": not bad}
    for b in bad:
        RES["behind"].append(f"hall_variant: {b}: re-run tools/ue_armorylab_shell.py as the LAST Unreal step (SYNC.md 3)")


def synced_rev(side):
    if side == "dojo":
        f = A.ROOT / "WorkFiles/dojo/build/unreal/armory_sync/synced_revision.json"
        notes = A.ROOT / "WorkFiles/dojo/build/BUILD_NOTES.md"
        key = "DojoLab"
    else:
        f = A.ROOT / "WorkFiles/armory/build/unreal/armory_hall_sync/synced_revision.json"
        notes = A.ROOT / "WorkFiles/armory/build/BUILD_NOTES.md"
        key = "ArmoryLab"
    rec = A.jload(f).get(key) if f.exists() else None
    note = None
    if notes.exists():
        hits = re.findall(r"armory_hall synced rev (\d+)", notes.read_text(encoding="utf-8", errors="replace"))
        note = int(hits[-1]) if hits else None
    return rec, note


def main():
    ap = argparse.ArgumentParser(description="SYNC.md section-8 checks")
    ap.add_argument("--side", choices=["armory", "dojo"], required=True)
    ap.add_argument("--json")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--skip-fresh", action="store_true", help="skip the regen comparison (it reads the armory data)")
    a = ap.parse_args()
    S = A.shared()
    M = S["manifest"]
    RES["info"]["manifest_revision"] = M["revision"]
    RES["info"]["last_change"] = M["change_log"][-1] if M.get("change_log") else None
    for name, fn in (("files", lambda: check_files(M)), ("sha", lambda: check_sha(M, S, a.side)),
                     ("pieces", lambda: check_pieces(M, S)), ("envelope", lambda: check_envelope(S)),
                     ("names", lambda: check_names(M, S)), ("lights", lambda: check_lights(S, a.side)),
                     ("fresh", (lambda: None) if a.skip_fresh else (lambda: check_fresh(S, a.side))),
                     ("masters", lambda: check_masters(M, a.side)), ("hall_variant", lambda: check_hall_variant(S, a.side))):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            fail(f"{name}: check crashed: {type(exc).__name__}: {exc}")
    rec, note = synced_rev(a.side)
    proj = rec if rec is not None else note
    project = "DojoLab" if a.side == "dojo" else "ArmoryLab"
    needed = int((M.get("sync_needed_rev") or {}).get(project, M["revision"]))
    RES["info"]["project_synced_revision"] = {"record": rec, "build_notes": note, "needed": needed,
                                              "manifest_last_synced": (M.get("last_synced") or {}).get(project)}
    if proj is None or int(proj) < needed:
        RES["behind"].append(f"revision: your project synced rev {proj}, it needs rev {needed} (manifest rev "
                             f"{M['revision']}): run your sync ({'Scripts/dojo/unreal/run_armory_sync.sh' if a.side == 'dojo' else 'SYNC.md 3: your own steps, then tools/ue_armorylab_shell.py last'})")
    lockf = A.ROOT / "WorkFiles/locks/armoryhall.json"
    RES["info"]["lock_ArmoryHall"] = A.jload(lockf) if lockf.exists() else "free"
    code = 1 if RES["fail"] else 3 if RES["stale"] else 2 if RES["behind"] else 0
    RES["exit_code"] = code
    RES["side"] = a.side
    if a.json:
        A.jdump(a.json, RES)
    verdict = {0: "PASS (synced)", 2: "PASS, SYNC NEEDED", 3: "STALE INTERIOR (regen pending)", 1: "FAIL"}[code]
    print(f"check_sync --side {a.side}: {verdict} | manifest rev {M['revision']}, your project rev {proj} "
          f"(needs rev {needed})")
    for k in ("fail", "stale", "behind", "warn"):
        for m in RES[k][:25]:
            print(f"  {k.upper()}: {m}")
    if not a.quiet:
        print("  info:", json.dumps(RES["info"], default=str)[:1500])
    return code


if __name__ == "__main__":
    sys.exit(main())
