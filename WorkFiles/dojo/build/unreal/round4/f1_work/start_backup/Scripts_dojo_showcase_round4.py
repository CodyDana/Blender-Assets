"""Showcase ROUND 4 (2026-09-29): the remaining buildings in the combined DojoLab layout (plain Python, no bpy / unreal).

Read by compose_showcase.py. The four round-4 kits replace the last grey-box buildings; only the trees, the outside
ground and the 1v1 gameplay pieces (the invisible boundary and the rear-alley fences, spec 4.6) stay grey-box.

  KITS             kit -> (FBX folder, texture folder, Unreal content root)
  LAYOUTS          each kit's own layout (pieces, instances, replaces_greybox), exactly as its track wrote it
  PROP_MOVES       the outbuildings track's measured proposals for the combined import (layout_outbuildings_checks.json
                   'outbuildings_proposed_moves'): the wall AC stood in front of the residence's lattice window, the
                   junction box's back sat 4 cm inside the storehouse granite band
  WALK_ROUTES      the tracks' new walk / CONTROL routes (their check layouts), merged into the showcase's
  MARKER_FITS      traversal markers re-fitted to the kits' own UCX hulls (route 7 and the plinth): marker -> piece,
                   which hull (by its top), and which box sides come from the hull
"""
import json
from pathlib import Path

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
BUILD = ROOT / "WorkFiles" / "dojo" / "build"
EXP = ROOT / "Exports" / "DojoKit"

KITS = {
    "outbuildings": (EXP / "Outbuildings", None, "/Game/DojoKit/Outbuildings"),   # library materials only
    "corridors": (EXP / "Corridors", None, "/Game/DojoKit/Corridors"),
    "shed": (EXP / "Shed", None, "/Game/DojoKit/Shed"),
    "pavilion": (EXP / "Pavilion", None, "/Game/DojoKit/Pavilion"),
}
LAYOUT_FILES = {
    "outbuildings": BUILD / "outbuildings" / "layout_outbuildings.json",
    "corridors": BUILD / "corridors" / "layout_corridors.json",
    "shed": BUILD / "shed_pavilion" / "layout_shed.json",
    "pavilion": BUILD / "shed_pavilion" / "layout_pavilion.json",
}
CHECK_LAYOUT_FILES = {
    "outbuildings": BUILD / "outbuildings" / "layout_outbuildings_checks.json",
    "corridors": BUILD / "corridors" / "layout_corridors_checks.json",
    "shed": BUILD / "shed_pavilion" / "layout_shed_checks.json",
    "pavilion": BUILD / "shed_pavilion" / "layout_pavilion_checks.json",
}
LAYOUTS = {k: json.loads(p.read_text(encoding="utf-8")) for k, p in LAYOUT_FILES.items()}


def replaced_greybox():
    """grey-box piece -> the round-4 kit that replaces it (SM_DGB_Pavilion_NoDrum is the showcase's drum-less copy)."""
    out = {}
    for kit, L in LAYOUTS.items():
        for n in L["replaces_greybox"]:
            out[n] = kit
    return out


def prop_moves():
    L = json.loads(CHECK_LAYOUT_FILES["outbuildings"].read_text(encoding="utf-8"))
    return L.get("outbuildings_proposed_moves", [])


def walk_routes(base):
    """The tracks' walk routes that the showcase does not have yet (name -> route)."""
    out = {}
    for kit, p in CHECK_LAYOUT_FILES.items():
        L = json.loads(p.read_text(encoding="utf-8"))
        for k, v in L["walk_routes"].items():
            if k not in base:
                out[k] = dict(v, source=f"round 4: {p.relative_to(BUILD).as_posix()}")
    return out


# marker -> (piece, hull pick, sides taken from the hull). 'top' picks the hull whose top is closest to that height;
# the bottom (z0) always stays the marker's own (the pad's +1.50 is marker_policy's).
MARKER_FITS = {
    "Shed_FrontBand": ("SM_DKS_Roof", {"top": 2.5, "min_y": 4.0}, "xy+top"),
    "Landing_PavilionPad": ("SM_DKV_EavePad", {"top": 3.25}, "xy+top"),
    "Pavilion_Plinth": ("SM_DKV_Plinth", {"top": 1.0, "largest": True}, "xy+top"),
}


# ground fill (measured, WorkFiles/dojo/build/unreal/round4/checks/ground_holes_r4.json): the ground kit's gravel stops at
# the GREY-BOX building footprints (Y 27.5 in front of the outbuildings, the grey-box corridor strips Y 29.5 / 32.5,
# X 7.0-7.5 / 36.5-37.0 where the grey-box corridor met the storehouse / residence). The round-4 buildings stand at the
# spec faces (Y 27.94, the corridor post lines), so the sky showed through the strips in between (the white-lilac bands
# in the first round-4 captures). The same kit's world-XY gravel panels fill them (pivot = min corner, rot 0; they join
# seamlessly); strips under closed floors and behind the buildings are filled too so no hole is left in the open air.
_W_FILL = [   # (piece, x0, y0) west side; the east side is the mirror about X 22 (x0' = 44 - x0 - width)
    ("SM_DKG_Gravel_4x0p5", 0.0, 27.5), ("SM_DKG_Gravel_2x0p5", 4.0, 27.5), ("SM_DKG_Gravel_1x0p5", 6.0, 27.5),
    ("SM_DKG_Gravel_0p5x0p5", 7.0, 27.5),                                   # in front of the storehouse face
    ("SM_DKG_Gravel_0p5x1", 7.0, 28.0), ("SM_DKG_Gravel_0p5x0p5", 7.0, 29.0),   # storehouse gable / corridor corner
    ("SM_DKG_Gravel_2x0p25", 7.5, 29.5), ("SM_DKG_Gravel_0p5x0p25", 9.5, 29.5),   # under the corridor deck, south edge
    ("SM_DKG_Gravel_2x0p25", 7.5, 32.25), ("SM_DKG_Gravel_0p5x0p25", 9.5, 32.25),  # under the deck, north edge
    ("SM_DKG_Gravel_0p5x2", 7.0, 32.5), ("SM_DKG_Gravel_0p5x1", 7.0, 34.5), ("SM_DKG_Gravel_0p5x0p5", 7.0, 35.5),
    ("SM_DKG_Gravel_4x0p5", 0.0, 35.5), ("SM_DKG_Gravel_2x0p5", 4.0, 35.5), ("SM_DKG_Gravel_1x0p5", 6.0, 35.5),
]


def _dims(piece):
    w, d = piece.rsplit("_", 1)[1].split("x")
    return float(w.replace("p", ".")), float(d.replace("p", "."))


GROUND_FILL = []
for _p, _x, _y in _W_FILL:
    _w, _d = _dims(_p)
    GROUND_FILL.append((_p, _x, _y))
    GROUND_FILL.append((_p, round(44.0 - _x - _w, 4), _y))
