"""Showcase traversal-marker fixes (round 2, 2026-09-28), shared by compose_showcase.py (Blender) and the plain-Python
patch of an existing layout_showcase.json (apply_marker_policy.py). No bpy / unreal imports.

1 Landing_PavilionPad: bottom raised from +1.25 to +1.50. GASP's forward trace is a capsule r 30 / half height 60 at
  the actor centre (feet + 86 + CMC hover 1.9-2.4 cm), so from the courtyard its top reaches +1.484 at most; with the
  pad's box starting at +1.25 the plinth route's stance (38.64, 3.0), 0.24 m from the pad's west face, started INSIDE
  the pad marker and traced TRV_Landing_PavilionPad instead of TRV_Pavilion_Plinth (verifier, in-engine sweep). From
  the crate top (+1.25) the same trace spans +1.529..+2.729, so the crate -> pad route still reaches the raised box.
2 Wall_S_W2 [18, 19.7] and Wall_S_E1 [24.3, 26]: the grey-box's wall stubs beside the gate. Kit 1 replaced them with
  the gate frame and the 0.49 m gate joins (world X 18.0-18.49 / 25.51-26.0, tops +2.0), which are shorter than
  GASP's 0.60 m minimum ledge, and the markers sat buried in SM_DK_Gate_Frame (12 / 12 probes failed the room check).
  No route uses them: removed.
"""
SUN_KELVIN = 5500   # the showcase sun's temperature at the light (round 2; see apply_round2.py / the round-2 notes)
SUN_NOTE = ("render_kit1.py sunset: 4.2 W/m2 x K 100 = 420 lux; 5500 K at the light (round 2): UE's atmosphere sun "
            "reddens a 13 deg sun by itself (colour probe: 6500 K reads as warm as Blender's sun colour), so the old "
            "4300 K double-warmed it (the orange cast); exposure from its +0.6 EV: bias = 0.6 - log2(K)")
PAD_NAME = "Landing_PavilionPad"
PAD_BOTTOM = 1.50
STALE = {"Wall_S_W2": "grey-box wall stub; kit 1's gate frame + 0.49 m gate join now stand there (join shorter than "
                      "GASP's 0.60 m min ledge; the marker was buried in SM_DK_Gate_Frame)",
         "Wall_S_E1": "grey-box wall stub; kit 1's gate frame + 0.49 m gate join now stand there (join shorter than "
                      "GASP's 0.60 m min ledge; the marker was buried in SM_DK_Gate_Frame)"}


def apply(markers, routes):
    """Mutates and returns (markers, report). Refuses to drop a marker a climb route still names."""
    used = {r.get("marker") for r in routes}
    rep = {"removed": {}, "raised": {}}
    keep = []
    for m in markers:
        if m["name"] in STALE:
            if m["name"] in used:
                raise ValueError(f"marker {m['name']} is used by a climb route; not removing it")
            rep["removed"][m["name"]] = {"box": m["box"], "why": STALE[m["name"]]}
            continue
        if m["name"] == PAD_NAME and m["box"][4] < PAD_BOTTOM:
            rep["raised"][m["name"]] = {"old_bottom": m["box"][4], "new_bottom": PAD_BOTTOM}
            m["box"][4] = PAD_BOTTOM
            m["note"] = (m.get("note", "") + f"; bottom +{PAD_BOTTOM:.2f} (round 2: clear of GASP's courtyard trace "
                         "capsule, top +1.484, so the plinth stance traces TRV_Pavilion_Plinth)")
        keep.append(m)
    markers[:] = keep
    return markers, rep
