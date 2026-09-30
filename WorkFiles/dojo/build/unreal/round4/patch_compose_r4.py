"""Round 4 (2026-09-29): one-off patch of Scripts/dojo/showcase/compose_showcase.py (the round-4 kits). Kept for the
record; the start copy is in start_backup/showcase_scripts/."""
from pathlib import Path

p = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\showcase\compose_showcase.py")
s = p.read_text(encoding="utf-8")


def rep(a, b, cnt=1):
    global s
    assert s.count(a) == cnt, (a[:80], s.count(a))
    s = s.replace(a, b)


rep('''import look_r3  # noqa: E402  (round 3: look-pass instance values, close-up cameras, the dropped-lamp rules)
''', '''import look_r3  # noqa: E402  (round 3: look-pass instance values, close-up cameras, the dropped-lamp rules)
import round4  # noqa: E402  (round 4: outbuildings, corridors, shed, pavilion replace the last grey-box buildings)
''')
rep('''REPLACED_GB.update({n: "hall" for n in LH["replaces_greybox"]})   # body, veranda, step band, roofs, eave pads
''', '''REPLACED_GB.update({n: "hall" for n in LH["replaces_greybox"]})   # body, veranda, step band, roofs, eave pads
KITS.update(round4.KITS)                  # round 4 (2026-09-29): the remaining buildings
LR4 = round4.LAYOUTS
REPLACED_GB.update(round4.replaced_greybox())   # storehouse, residence, corridors, shed, pavilion (+ NoDrum, pad)
R4_KITS = tuple(round4.KITS)
''')
rep('''    P.pop("SM_DGB_Pavilion")
    P[PAVILION_NODRUM] = {"kit": "showcase", "class": "building", "folder": "Yard", "nanite": False,
                          "note": "grey-box drum pavilion without its drum (the taiko kit replaces it)"}
''', '''    if PAVILION_NODRUM not in REPLACED_GB:   # round 4: the pavilion kit replaces the drum-less grey-box pavilion
        P.pop("SM_DGB_Pavilion")
        P[PAVILION_NODRUM] = {"kit": "showcase", "class": "building", "folder": "Yard", "nanite": False,
                              "note": "grey-box drum pavilion without its drum (the taiko kit replaces it)"}
''')
rep('''    for name, p in P.items():
        d = KITS[p["kit"]][0]
''', '''    for kit, LK in LR4.items():   # round 4: each kit's own Nanite flags (pieces of about 2k tris or more)
        for name, p in LK["pieces"].items():
            P[name] = {"kit": kit, "class": p["class"], "folder": p["folder"], "nanite": bool(p["nanite"]),
                       "note": p.get("note", "")[:160]}
    for name, p in P.items():
        d = KITS[p["kit"]][0]
''')
rep('''def matrix_of(i):''', '''def round4_instances():
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


def matrix_of(i):''')
rep('''    # the pavilion without its drum (from the grey-box export)
    meta["SM_DGB_Pavilion"] = import_piece("SM_DGB_Pavilion", EXP / "SM_DGB_Pavilion.fbx")
''', '''    # the pavilion without its drum (from the grey-box export); round 4: gone, the pavilion kit replaces it
    if PAVILION_NODRUM in P:
        compose_nodrum(P, meta, kit_objs)
    finish_main(P, meta, kit_objs)


def compose_nodrum(P, meta, kit_objs):
    meta["SM_DGB_Pavilion"] = import_piece("SM_DGB_Pavilion", EXP / "SM_DGB_Pavilion.fbx")
''')
rep('''                             "ucx_bbox": None}
    for name, p in P.items():
        p.update({k: meta[name][k] for k in ("slots", "tris", "lod_tris", "lods", "n_ucx", "vcol")})
        if p["kit"] not in ("kit1", "greybox", "showcase", "ground", "hall"):''', '''                             "ucx_bbox": None}


def finish_main(P, meta, kit_objs):
    for name, p in P.items():
        p.update({k: meta[name][k] for k in ("slots", "tris", "lod_tris", "lods", "n_ucx", "vcol")})
        if p["kit"] not in ("kit1", "greybox", "showcase", "ground", "hall") + R4_KITS:''')
rep('''    REPORT["fits"] = fit_climb_props(props, meta)
    instances = base + ground + props + hall
''', '''    REPORT["fits"] = fit_climb_props(props, meta)
    REPORT["round4_prop_moves"] = apply_prop_moves(props)
    r4 = round4_instances()
    instances = base + ground + props + hall + r4
''')
rep('''    _, REPORT["marker_policy"] = marker_policy.apply(markers, climb_routes)
''', '''    REPORT["round4_marker_fits"] = fit_round4_markers(markers, r4, kit_objs)
    _, REPORT["marker_policy"] = marker_policy.apply(markers, climb_routes)
''')
rep('''                                                          "wall's outer face is what stops a 1v1 player at the gate")
''', '''                                                          "wall's outer face is what stops a 1v1 player at the gate")
    REPORT["round4_walk_routes"] = sorted(round4.walk_routes(walk))
    walk.update(round4.walk_routes(walk))
''')
rep('''                    "hall": "hall/layout_hall.json (kits 3 + 4 f1)"},
        "round": "showcase r3 (combined import round 3, look pass, 2026-09-28)", "hall": LH["numbers"],''', '''                    "hall": "hall/layout_hall.json (kits 3 + 4 f1; round-4 ridges)",
                    "round4": {k: v.relative_to(BUILD).as_posix() for k, v in round4.LAYOUT_FILES.items()}},
        "round": "showcase r4 (combined import round 4, the remaining buildings, 2026-09-29)", "hall": LH["numbers"],
        "round4_numbers": {k: v.get("numbers", {}) for k, v in LR4.items()},''')
rep('''        "replaced_greybox": sorted(set(REPLACED_GB) | set(L1["kit1"]["replaced_greybox"]) | {"SM_DGB_Pavilion"}),''', '''        "replaced_greybox": sorted(set(REPLACED_GB) | set(L1["kit1"]["replaced_greybox"]) | {"SM_DGB_Pavilion"}),
        "greybox_kept": sorted({i["piece"] for i in instances if i["kit"] == "greybox"}),''')
p.write_text(s, encoding="utf-8")
print("patched")
