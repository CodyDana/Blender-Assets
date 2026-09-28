"""Walk-in clearance for a Manny-sized capsule, measured against the kit's UCX collision hulls (the same hulls Unreal
imports: hull counts verified equal by ak_verify). Unreal's capsule traces do not collide in a -nullrhi commandlet (the
control sweep into case 1 passed straight through), so the geometric check runs here instead.

Capsule: radius 0.35 m, blocking band z 0.20-1.80 m (anything lower is a step the character walks up: max 0.45 m on the
character movement component; our steps are 0.15 m). A route point is clear when no hull whose z range overlaps the band
comes within the radius horizontally. Every hull is an axis-aligned box after the instance rotations (multiples of 90 deg).
A control route straight into case 1 must be blocked, or the check is invalid.

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
ROUTES = {
    # layout 2 r4: the inset mat is X 4.0-8.0, Y -0.30-0.75 (+0.15), the threshold the outer sill Y -0.435 to -0.30
    "outside_through_entrance_to_mat": [(6.0, -2.0), (6.0, 0.45)],    # over the sill onto the inset mat (+0.15)
    # layout 2 r3: the step platform (r4: +0.15, X 2.15-9.85, to the post fronts at Y 0.86) round the inset mat replaces
    # the 6 cm sill beam at Y 2.56 (r2 ran to Y 1.58); this route steps down off its front board toward case 1
    "mat_over_entry_platform_to_case1": [(6.0, 0.45), (6.0, 2.55), (5.2, 2.65)],
    # layout 2: the vestibule posts are gone (the jamb posts now stand on the south wall line at the frame's outer
    # ends, r3: plinths X 1.57-2.15 / 9.85-10.43, Y 0-0.84); these start on the floor in front of the step and still
    # pass the floor lanterns at (3.90 / 8.10, 2.25)
    "mat_to_west_aisle_to_steps": [(6.0, 1.2), (4.8, 1.65), (3.0, 1.65), (3.0, 12.3)],   # aisle X 2.3-5.0
    "mat_to_east_aisle_to_steps": [(6.0, 1.2), (7.2, 1.65), (9.0, 1.65), (9.0, 12.3)],   # aisle X 7.0-9.7
    "west_wall_walk_along_niches": [(3.0, 1.5), (0.75, 1.5), (0.75, 12.9)],        # behind the west side cases
    "east_wall_walk_along_niches": [(9.0, 1.5), (11.25, 1.5), (11.25, 12.9)],      # behind the east side cases
    "centre_gap_case1_case2": [(3.0, 5.7), (9.0, 5.7)],                            # aisle to aisle, Y 4.4-7.0
    "centre_gap_case2_case3": [(3.0, 9.5), (9.0, 9.5)],                            # aisle to aisle, Y 8.2-10.8
    "aisle_up_the_steps_to_hero_table": [(9.0, 12.25), (6.0, 12.25), (6.0, 13.95)],  # hero table front at Y 14.39
    # building r5: from the top of the steps across the platform to the rear alcoves (between the heavy platform-front
    # posts, the hero table and the platform lanterns)
    # f1: the rear alcoves moved outboard (X 1.2-3.0 / 9.0-10.8), the platform lanterns to (3.55 / 8.45, 15.10)
    "platform_to_west_rear_alcove": [(6.0, 12.25), (6.0, 13.95), (4.4, 13.95), (2.1, 14.4), (2.1, 14.95)],
    "platform_to_east_rear_alcove": [(6.0, 12.25), (6.0, 13.95), (7.6, 13.95), (9.9, 14.4), (9.9, 14.95)],
    # layout 2 (entrance.png's composition): from the mat along the inside of the south wall over the step platform,
    # past the parked leaves (r3: X 2.25-3.95 / 8.05-9.75, standing on the step, room face Y 0.19 + hardware) and the
    # inner jamb bands (X 2.11-2.25 / 9.75-9.89, to Y 0.215) up to the deep jamb posts at the frame's outer ends (r3:
    # plinths X 1.57-2.15 / 9.85-10.43, Y 0-0.84; the sconces on their room faces hang above the band), then off the
    # step's front board into the room beside them
    "inside_along_west_parked_leaf_to_jamb_post": [(6.0, 0.6), (2.6, 0.6), (2.6, 1.9)],
    "inside_along_east_parked_leaf_to_jamb_post": [(6.0, 0.6), (9.4, 0.6), (9.4, 1.9)],
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


def probe(x, y, floor):
    """-> (blocking hull or None, new floor). Hulls within the radius whose top is within STEP of the current floor are
    stepped onto (the floor rises to their top); anything taller that reaches into the body blocks."""
    new_floor = floor
    near = []
    for (x0, x1, y0, y1, z0, z1, name) in hulls:
        dx = max(x0 - x, 0.0, x - x1)
        dy = max(y0 - y, 0.0, y - y1)
        if (dx * dx + dy * dy) ** 0.5 < R:
            near.append((z0, z1, name, dx == 0.0 and dy == 0.0))
    for z0, z1, name, under in near:
        if z1 <= floor + STEP:
            if under:
                new_floor = max(new_floor, z1)
        elif z0 < floor + Z1:
            return name, floor
    return None, new_floor


res = {"capsule": {"radius_m": R, "band_z_m": [Z0, Z1]}, "n_hulls": len(hulls), "routes": {}}
for name, pts in ROUTES.items():
    hits = []
    floor = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(2, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / 0.05))
        for i in range(n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            b, floor = probe(x, y, floor)
            if b:
                hits.append({"at_m": [round(x, 2), round(y, 2)], "hull_of": b, "floor_m": round(floor, 3)})
                break
        if hits:
            break
    res["routes"][name] = {"points": pts, "clear": not hits, "first_block": hits[0] if hits else None,
                          "end_floor_m": round(floor, 3)}
res["control_blocked"] = all(not r["clear"] for k, r in res["routes"].items() if k.startswith("CONTROL"))
res["passed"] = res["control_blocked"] and all(r["clear"] for k, r in res["routes"].items() if not k.startswith("CONTROL"))
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print("WALK", json.dumps({k: (v["clear"], v["first_block"]) for k, v in res["routes"].items()}), "passed", res["passed"])
