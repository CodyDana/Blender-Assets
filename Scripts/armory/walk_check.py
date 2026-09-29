"""Walk-in clearance for a Manny-sized capsule, measured against the kit's UCX collision hulls (the same hulls Unreal
imports: hull counts verified equal by ak_verify). Unreal's capsule traces do not collide in a -nullrhi commandlet (the
control sweep into case 1 passed straight through), so the geometric check runs here instead.

Capsule: radius 0.35 m, blocking band z 0.20-1.80 m (anything lower is a step the character walks up: max 0.45 m on the
character movement component; our steps are 0.15 m). A route point is clear when no hull whose z range overlaps the band
comes within the radius horizontally. Every hull is an axis-aligned box after the instance rotations (multiples of 90 deg).
A control route straight into case 1 must be blocked, or the check is invalid.

Genkan (2026-09-28): the entry is a SUNKEN vestibule (build_armory_kit GENKAN: floor -0.12, X 3.52-8.48 (entryfix; was 2.17-9.83), Y 0-2.35 (entryfix r2; was 2.56), the
doorway X 4-8 back to Y -0.30) behind a
low sill (+0.04) with the black step beam (Y 2.35-2.51 since entryfix r2, flush with the hall floor) at its far edge, so the floor now also
steps DOWN: under the capsule centre the floor is the highest hull top within STEP of the current floor (it was only ever
raised). Every route reports its largest single step up and down (max_step_up_m / max_step_down_m, 5 cm probes); the
entry's steps must stay <= ENTRY_STEP_MAX (0.18 m), checked on the ENTRY_ROUTES and required for "passed".

Run: blender -b --factory-startup Assets/Armory/ArmoryKit.blend --python Scripts/armory/walk_check.py
Result: WorkFiles/armory/build/walk_check.json
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(bpy.data.filepath).resolve().parents[2]
OUT = ROOT / "WorkFiles" / "armory" / "build" / "walk_check.json"
if Path(bpy.data.filepath).name != "ArmoryKit.blend":   # a test copy (build_armory_kit --preview-dir): report beside it
    OUT = Path(bpy.data.filepath).resolve().parent / "walk_check.json"
R, Z0, Z1 = 0.35, 0.20, 1.80
# building stage (2026-09-27): routes for the 12 x 16 m hall (layout.json "cases"), the 4 m entrance and the platform
ENTRY_STEP_MAX = 0.18   # genkan: the largest single step allowed on the entry routes (sill down, beam up)
ROUTES = {
    # genkan (2026-09-28): over the low sill (Y -0.435 to -0.30, +0.04) down onto the sunken genkan floor (-0.12, X
    # 2.17-9.83, Y 0-2.56, the doorway X 4-8 back to the sill) and the rush mat lying on it (X 4.75-7.25, Y 0.18-2.56,
    # +2.2 cm; its board surround +3 cm)
    "outside_through_entrance_to_mat": [(6.0, -2.0), (6.0, 0.45)],
    # up the black step beam (Y 2.56-2.72, flush with the hall floor: one 12 cm step) onto the hall, toward case 1's
    # west corner (plinth X 5.1-6.9 from Y 3.05; entryfix: the entry lanterns are the andon SM_AK_Lantern on the genkan
    # floor at X 3.53-3.99 / 8.01-8.47, Y 2.093-2.553, against the bar; the genkan is X 3.52-8.48, the bar X 3.46-8.54;
    # entryfix r2: the lanterns stand 0.32 m in front of the bar, Y 1.57-2.03, and the bar is Y 2.35-2.51)
    "mat_up_the_step_beam_to_case1": [(6.0, 0.45), (6.0, 2.2), (4.45, 2.9)],
    # straight up the beam on the axis to just in front of case 1 (its plinth front Y 3.05)
    "genkan_axis_up_the_beam": [(6.0, 1.2), (6.0, 2.65)],
    # between the mat's surround (r4: X 4.60-7.40) and the west lantern (entryfix: X 3.53-3.99), up the bar beside it
    "genkan_up_the_beam_beside_west_lantern": [(4.45, 0.6), (4.45, 2.9)],
    "genkan_up_the_beam_beside_east_lantern": [(7.55, 0.6), (7.55, 2.9)],
    # layout 2: the vestibule posts are gone (the jamb posts stand on the south wall line at the frame's outer ends, r3:
    # plinths X 1.57-2.15 / 9.85-10.43, Y 0-0.84). Genkan: across the genkan floor in front of the entry lanterns
    # (entryfix: their fronts at Y 2.093) and up over the pit's side return onto the hall floor (one 12 cm step), then
    # up the aisle
    # entryfix r2: in front of the lanterns (their fronts now at Y 1.57), so Y 1.65 -> 1.1
    # rear dais (2026-09-28): the flight's foot is Y 12.30 (X 3.80-8.20, cheek blocks X 3.45-3.80 / 8.20-8.55 from
    # Y 12.30), the stair-foot lanterns on their stands X 2.95-3.41 / 8.59-9.05, Y 12.62-13.08: up the aisle to Y 11.92,
    # in front of the cheek block (its cap from Y 12.29) to the flight and up its five 0.15 m risers onto the landing (+0.75)
    "mat_to_west_aisle_to_steps": [(6.0, 1.2), (4.8, 1.1), (3.0, 1.1), (3.0, 11.92), (4.3, 11.92), (4.3, 13.9)],
    "mat_to_east_aisle_to_steps": [(6.0, 1.2), (7.2, 1.1), (9.0, 1.1), (9.0, 11.92), (7.7, 11.92), (7.7, 13.9)],
    "west_wall_walk_along_niches": [(3.0, 1.5), (0.75, 1.5), (0.75, 12.9)],        # behind the west side cases
    "east_wall_walk_along_niches": [(9.0, 1.5), (11.25, 1.5), (11.25, 12.9)],      # behind the east side cases
    "centre_gap_case1_case2": [(3.0, 5.7), (9.0, 5.7)],                            # aisle to aisle, Y 4.4-7.0
    "centre_gap_case2_case3": [(3.0, 9.5), (9.0, 9.5)],                            # aisle to aisle, Y 8.2-10.8
    # rear dais: case 3's back is Y 11.8 (X 5.2-6.8); up the flight on a slant onto the landing, the hero table front
    # at Y 14.55 on the +0.90 deck
    "aisle_up_the_steps_to_hero_table": [(9.0, 11.92), (7.7, 11.92), (6.0, 13.95)],
    # building r5: from the top of the steps across the platform to the rear alcoves (between the heavy platform-front
    # posts, the hero table and the platform lanterns)
    # f1: the rear alcoves moved outboard (X 1.2-3.0 / 9.0-10.8), the platform lanterns to (3.55 / 8.45, 15.10)
    # rear dais: up the flight to the landing (+0.75), across onto the side plinth (b4: +0.90 from Y 13.50, one 0.15 m
    # step at X 3.80 / 8.20) to the alcove front (Y 15.40); the deck lanterns stand at X 3.27-3.73 / 8.27-8.73,
    # Y 14.87-15.33
    "platform_to_west_rear_alcove": [(6.0, 12.25), (6.0, 13.95), (4.3, 14.2), (2.1, 14.25), (2.1, 14.95)],
    "platform_to_east_rear_alcove": [(6.0, 12.25), (6.0, 13.95), (7.7, 14.2), (9.9, 14.25), (9.9, 14.95)],
    # rear dais: on to the corner showcases (b4: X 0.39-1.19 / 10.81-11.61, front Y 15.395), clear of the sill ledge
    # (X 0-0.335 / 11.665-12, underside +2.55: head height on the +0.90 deck)
    "platform_to_west_corner_showcase": [(6.0, 12.25), (6.0, 13.95), (4.3, 14.2), (2.1, 14.25), (0.73, 14.95)],
    "platform_to_east_corner_showcase": [(6.0, 12.25), (6.0, 13.95), (7.7, 14.2), (9.9, 14.25), (11.27, 14.95)],
    # rear dais: up the flight on the axis and the deck riser to the hero table's front (Y 14.55)
    # b4: the table is Y 14.90-15.80 now: on up the plain deck riser onto the deck in front of it
    "axis_up_the_flight_to_hero_table_front": [(6.0, 12.25), (6.0, 14.50)],
    # b4: the side plinths are +0.90 from the landing front (Y 13.50): from the landing across onto the west / east
    # plinth (one 0.15 m step at X 3.80 / 8.20), past the newel side walls (to Y 13.50) and the heavy posts (Y 13.18-13.48)
    # b7: the side zones are terraced in the flight's rows (cabinet +0.60 from Y 13.56, tread +0.75 from 13.98, deck
    # +0.90 from 14.40): along the +0.60 row (Y 13.85: 0.37 m behind the heavy posts' back faces, Y 13.48) across the
    # full width of the room
    "flight_onto_west_side_terrace": [(5.0, 13.85), (0.8, 13.85)],
    "flight_onto_east_side_terrace": [(7.0, 13.85), (11.2, 13.85)],
    # layout 2 (entrance.png's composition): from the mat along the inside of the south wall across the genkan floor,
    # past the parked leaves (X 2.25-3.95 / 8.05-9.75, genkan: standing on its floor, room face Y 0.19 + hardware) and the inner jamb bands (X 2.11-2.25 / 9.75-9.89, to Y 0.215) up to the deep jamb
    # posts at the frame's outer ends (plinths X 1.57-2.15 / 9.85-10.43, Y 0-0.84; the sconces on their room faces hang
    # above the band); entryfix: up over the pit's side return (X 3.46-3.52 / 8.48-8.54) onto the hall floor, which
    # runs on outboard of the genkan to the posts
    "inside_along_west_parked_leaf_to_jamb_post": [(6.0, 0.6), (2.6, 0.6), (2.6, 1.9)],
    "inside_along_east_parked_leaf_to_jamb_post": [(6.0, 0.6), (9.4, 0.6), (9.4, 1.9)],
    # genkan: from the vestibule's west / east end up over the side return (one 12 cm step) onto the hall floor beside
    # the post plinth (to Y 0.86) and on to the wall walk behind the side cases (entryfix: the genkan ends at X 3.52 /
    # 8.48, so the start moved in from X 3.0 / 9.0, beside the mat surround)
    # entryfix r2: in front of the lanterns (fronts Y 1.57) and past the post plinth (to Y 0.84) on a slant
    "genkan_west_end_up_the_return_to_wall_walk": [(4.2, 1.1), (3.0, 1.15), (1.1, 1.4), (0.75, 2.0)],
    "genkan_east_end_up_the_return_to_wall_walk": [(7.8, 1.1), (9.0, 1.15), (10.9, 1.4), (11.25, 2.0)],
    "CONTROL_must_hit_case1": [(6.0, 1.2), (6.0, 3.6)],
    # exterior stage (2026-09-27): the player starts in the courtyard (layout.json "player_start", on the path inside the
    # gate) and walks the stepping stones and the ishidatami over the landing and the threshold into the hall
    "courtyard_start_along_path_through_entrance": [(6.0, -10.4), (6.1, -7.5), (6.0, -4.9), (6.0, -1.9), (6.0, -0.4),
                                                    (6.0, 1.2)],
    "outside_through_gate_to_start": [(6.0, -16.0), (6.0, -13.0), (6.0, -10.4)],   # gate clear X 4.81-7.19
    "courtyard_round_west_to_tsukubai_front": [(6.0, -10.4), (4.7, -8.8), (4.7, -6.4)],
    "courtyard_round_east_past_lantern": [(6.0, -4.0), (9.6, -4.4), (9.6, -8.6), (6.2, -9.0)],
    "CONTROL_must_hit_stone_lantern": [(6.0, -7.3), (8.35, -7.3)],
}

# exterior stage: the SM_AKX_ garden pieces live in KitExterior / AssemblyExterior
KIT_COLLS, ASM_COLLS = ("Kit", "KitExterior"), ("Assembly", "AssemblyExterior")
kit = {o.name: o for c in KIT_COLLS if c in bpy.data.collections for o in bpy.data.collections[c].objects
       if o.type == "MESH" and not o.name.startswith("UCX_")}
hulls = []   # (xmin, xmax, ymin, ymax, zmin, zmax, instance name)
for inst in [o for c in ASM_COLLS if c in bpy.data.collections for o in bpy.data.collections[c].objects]:
    piece = inst.name.split("__")[0]
    src = kit.get(piece)
    if src is None:
        continue
    for h in src.children:
        if not h.name.startswith("UCX_"):
            continue
        pts = [inst.matrix_world @ (h.matrix_local @ Vector(c)) for c in h.bound_box]
        xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
        hulls.append((min(xs), max(xs), min(ys), max(ys), min(zs), max(zs), inst.name))


STEP = 0.45   # CharacterMovement MaxStepHeight (cm 45)
ENTRY_ROUTES = ("outside_through_entrance_to_mat", "mat_up_the_step_beam_to_case1", "genkan_axis_up_the_beam",
                "genkan_up_the_beam_beside_west_lantern", "genkan_up_the_beam_beside_east_lantern",
                "mat_to_west_aisle_to_steps", "mat_to_east_aisle_to_steps", "inside_along_west_parked_leaf_to_jamb_post",
                "inside_along_east_parked_leaf_to_jamb_post", "genkan_west_end_up_the_return_to_wall_walk",
                "genkan_east_end_up_the_return_to_wall_walk", "courtyard_start_along_path_through_entrance")


def probe(x, y, floor):
    """-> (blocking hull or None, new floor). Hulls within the radius whose top is within STEP of the current floor are
    stepped onto; anything taller that reaches into the body blocks. Genkan: the new floor is the highest top of the
    hulls directly under the capsule centre (within STEP of the current floor), so it can also step down (a sunken
    floor); with no hull under the centre it stays where it was."""
    under_tops = []
    near = []
    for (x0, x1, y0, y1, z0, z1, name) in hulls:
        dx = max(x0 - x, 0.0, x - x1)
        dy = max(y0 - y, 0.0, y - y1)
        if (dx * dx + dy * dy) ** 0.5 < R:
            near.append((z0, z1, name, dx == 0.0 and dy == 0.0))
    for z0, z1, name, under in near:
        if z1 <= floor + STEP:
            if under:
                under_tops.append(z1)
        elif z0 < floor + Z1:
            return name, floor
    return None, (max(under_tops) if under_tops else floor)


res = {"capsule": {"radius_m": R, "band_z_m": [Z0, Z1]}, "n_hulls": len(hulls), "routes": {}}
for name, pts in ROUTES.items():
    hits = []
    floor = None
    up = down = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(2, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / 0.05))
        for i in range(n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if floor is None:   # the start: the highest ground-level top (<= +0.7) under the first point
                floor = max([h[5] for h in hulls if h[0] <= x <= h[1] and h[2] <= y <= h[3] and h[5] <= 0.7] or [0.0])
            b, nf = probe(x, y, floor)
            up, down = max(up, nf - floor), max(down, floor - nf)
            floor = nf
            if b:
                hits.append({"at_m": [round(x, 2), round(y, 2)], "hull_of": b, "floor_m": round(floor, 3)})
                break
        if hits:
            break
    res["routes"][name] = {"points": pts, "clear": not hits, "first_block": hits[0] if hits else None,
                          "end_floor_m": round(floor, 3), "max_step_up_m": round(up, 3),
                          "max_step_down_m": round(down, 3)}
res["control_blocked"] = all(not r["clear"] for k, r in res["routes"].items() if k.startswith("CONTROL"))
res["entry_step_max_m"] = ENTRY_STEP_MAX
res["entry_steps_ok"] = all(max(res["routes"][k]["max_step_up_m"], res["routes"][k]["max_step_down_m"]) <= ENTRY_STEP_MAX
                            for k in ENTRY_ROUTES)
res["passed"] = res["control_blocked"] and res["entry_steps_ok"] and \
    all(r["clear"] for k, r in res["routes"].items() if not k.startswith("CONTROL"))
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print("WALK", json.dumps({k: (v["clear"], v["first_block"], v["max_step_up_m"], v["max_step_down_m"])
                          for k, v in res["routes"].items()}), "entry_steps_ok", res["entry_steps_ok"], "passed",
      res["passed"])
