"""Items on display (the user adds them one at a time). Imported by build_armory_kit.py (setup(globals()) gives it the
Piece class and the case table).

Item 1 (user, 2026-09-27): "Just have one tray displaying all of them neatly", revised the same day: "The tray should look
like the reference image. it's a flat black slate-looking tray": the six finished shuriken forms laid straight on one flat
honed charcoal-slate board (no walls, no compartments), with a small blank brass plate on its front edge, as reference 2's
display boards, in case 8 (the front case on the east aisle, the shuriken case in armory3_reference). Two neat rows:
  back:  FourPoint   EightPoint  SixPoint
  front: SquarePlate HookedCross Spike
Every disc lies flat, presented face (+Z) up, turned so the arm that carries its Grip socket points straight back (+Y
of the tray): one consistent, tidy orientation. The HookedCross is only ever rotated, never mirrored (no negative scale
anywhere: mirroring it makes the forbidden symbol). The spike lies along the tray's width, point to the viewer's right.

Sources: Exports/Shuriken/SM_Shuriken_<Form>.fbx + .sockets.json (Grip socket locations are Unreal cm in the item's own
frame: Blender y = -Unreal y). In Unreal the items are the pack's own imported assets /Game/NinjaPack/Meshes/... (sockets
recreated, pack materials), copied into ArmoryLab by make_project.py.
"""
import json
import math
from pathlib import Path

G = {}
ROOT = Path(__file__).resolve().parents[2]
SHURIKEN = ROOT / "Exports" / "Shuriken"

# board (metres, board-local frame: X across, Y away from the viewer, Z up, origin at the centre of the base)
CELL, DIV, WALL = 0.165, 0.008, 0.015            # the item grid pitch (CELL + DIV) and edge margin, as before
TRAY_W = 3 * CELL + 2 * DIV + 2 * WALL           # 0.541
TRAY_D = 2 * CELL + DIV + 2 * WALL               # 0.368
SLAB_T = 0.025                                   # a 2.5 cm slate slab lying on the deck
LINING_TOP = SLAB_T                              # the items rest on the slate
DECK_ABOVE_PLINTH = 0.004                        # the case deck is H .. H + 0.004
CASE_LABEL = "8"
# form, row (0 = back, 1 = front), column, presented thickness (m)
LAYOUT = [("FourPoint", 0, 0, 0.0030), ("EightPoint", 0, 1, 0.0025), ("SixPoint", 0, 2, 0.0020),
          ("SquarePlate", 1, 0, 0.0019), ("HookedCross", 1, 1, 0.0025), ("Spike", 1, 2, 0.0060)]
SLATE, PLATE, CARD = "M_AK_Slate", "M_AK_Brass", "M_AK_ReflectCard"
# the metal items are near-mirror (metallic 1): they show what they reflect, and from the aisle a flat star reflects the
# back of the case, so under a top light alone they read black while the matte slate goes grey. A softly lit panel at
# the back of the deck (the jeweller's reflection card; reference 2's cases have lit interiors) is what the star faces
# reflect toward a viewer in the aisle, so the steel glows and the slate stays dark
MATERIALS = {SLATE: ("Slate", 0.5, {}),
             CARD: (None, 1.0, {"color": "#A88C62", "emit": 0.22, "emit_color": "#FFB45C"})}   # r2: 1.2 read as a white lightbox; 0.35 still a bright panel
CARD_GAP, CARD_H = 0.06, 0.20      # r2: the reflections land at +0.08 to +0.17 (27 deg aisle view), so 0.20 is enough
# the case light over a case that holds items, as a factor on its power (the empty-deck tuning is 1.0). The dark slate
# needs the light back (the pale kiri tray had needed 0.12)
CASE_LIGHT = {"8": 0.08}   # dim: the slate must read near-black; the card lights the steel


def case_light_scale(label):
    return CASE_LIGHT.get(label, 1.0)


def setup(ns):
    global G
    G = ns


def tray_piece():
    """SM_AK_DSP_ShurikenTray: one flat honed-slate slab with a small blank brass plate on its front edge (one UCX)."""
    p = G["Piece"]("SM_AK_DSP_ShurikenTray")
    hw, hd = TRAY_W / 2, TRAY_D / 2
    p.box(-hw, hw, -hd, hd, 0, SLAB_T, SLATE, uv="x")
    p.box(-0.035, 0.035, -hd - 0.002, -hd, 0.006, 0.019, PLATE)    # blank plate (no text), centred on the front edge
    p.box(-hw, hw, hd + CARD_GAP, hd + CARD_GAP + 0.008, 0, SLAB_T + CARD_H, CARD)   # lit reflection card
    p.col(-hw, hw, -hd - 0.002, hd + CARD_GAP + 0.008, 0, SLAB_T + CARD_H)
    return p


def cell_centre(row, col):
    x = -TRAY_W / 2 + WALL + CELL / 2 + col * (CELL + DIV)
    y = (CELL + DIV) / 2 if row == 0 else -(CELL + DIV) / 2
    return x, y


def grip_angle_deg(form):
    """Angle of the Grip socket in the item's Blender frame (sidecar is Unreal cm: Blender y = -Unreal y)."""
    d = json.loads((SHURIKEN / f"SM_Shuriken_{form}.sockets.json").read_text(encoding="utf-8"))
    g = next(s for s in d["sockets"] if s["socket"] == "Grip")
    x, y = g["location_cm"][0], -g["location_cm"][1]
    return math.degrees(math.atan2(y, x))


def case_of(label):
    lab, t, x, y, r = next(c for c in G["CASE_TABLE"] if c[0] == label)
    return t, x, y, r


def tray_instance():
    """(piece, x, y, z, rot_z) of the tray (build_armory_kit.layout's add() signature): centred on case 8's deck,
    front row toward the case front (the aisle)."""
    t, x, y, r = case_of(CASE_LABEL)
    z = G["CASES"][t][2] + DECK_ABOVE_PLINTH
    return "SM_AK_DSP_ShurikenTray", x, y, round(z, 4), r


def items():
    """World placement of every shuriken: Blender metres + rotation about Z (degrees). Flat items: yaw only."""
    _piece, cx, cy, cz, r = tray_instance()
    ca, sa = math.cos(math.radians(r)), math.sin(math.radians(r))
    out = []
    for form, row, col, thick in LAYOUT:
        lx, ly = cell_centre(row, col)
        if form == "Spike":
            yaw = 0.0                                   # along the tray width, point to the viewer's right (+X)
        else:
            yaw = 90.0 - grip_angle_deg(form)          # the Grip arm points straight back (+Y of the tray)
        wx, wy = cx + ca * lx - sa * ly, cy + sa * lx + ca * ly
        wz = cz + LINING_TOP + thick / 2 + 0.0005      # origin at mid-thickness, 0.5 mm clear of the slate
        out.append({"name": f"Shuriken_{form}", "form": form, "case": CASE_LABEL,
                    "fbx": str(SHURIKEN / f"SM_Shuriken_{form}.fbx"),
                    "textures": str(SHURIKEN / "Textures" / f"T_Shuriken_{form}"),
                    "ue_asset": f"/Game/NinjaPack/Meshes/SM_Shuriken_{form}",
                    "loc": [round(wx, 5), round(wy, 5), round(wz, 5)],
                    "rot_z": round((r + yaw) % 360.0, 4), "mirror": False})
    return out


def import_items(item_list, coll):
    """Blender preview only: the real FBX LOD0 of each item at its display transform, with its baked maps."""
    import bpy
    from mathutils import Matrix
    report = []
    for it in item_list:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=it["fbx"], axis_forward="-Y", axis_up="Z")
        new = [o for o in bpy.data.objects if o not in before]
        lod0 = next(o for o in new if o.type == "MESH" and o.name.endswith("_LOD0") and not o.name.startswith("UCX_"))
        mesh_world = lod0.matrix_world.copy()
        for o in new:
            if o is not lod0:
                bpy.data.objects.remove(o, do_unlink=True)
        lod0.parent = None
        for c in list(lod0.users_collection):
            c.objects.unlink(lod0)
        coll.objects.link(lod0)
        lod0.name = f"ITEM_{it['name']}"
        # the imported frame must be the build frame (identity up to the FBX unit handling): check, then place
        dims = [round(v, 4) for v in lod0.dimensions]
        lod0.matrix_world = (Matrix.Translation(it["loc"]) @ Matrix.Rotation(math.radians(it["rot_z"]), 4, "Z")
                             @ Matrix.LocRotScale(None, mesh_world.to_quaternion(), mesh_world.to_scale()))
        lod0.data.materials.clear()
        lod0.data.materials.append(item_material(it))
        report.append({"name": it["name"], "dims_m": dims, "import_scale": [round(v, 4) for v in mesh_world.to_scale()],
                       "import_rot_deg": [round(math.degrees(a), 3) for a in mesh_world.to_euler()]})
    return report


def item_material(it):
    """Principled material from the item's baked BC / ORM / N (N is DirectX: green flipped back for Blender)."""
    import bpy
    stem = it["textures"]
    mat = bpy.data.materials.new(f"MI_Preview_{it['name']}")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def img(suffix, noncolor):
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(f"{stem}_{suffix}.png", check_existing=True)
        if noncolor:
            node.image.colorspace_settings.name = "Non-Color"
        return node
    bc, orm, nrm = img("BC", False), img("ORM", True), img("N", True)
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
    sn = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(nrm.outputs["Color"], sn.inputs["Color"])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sn.outputs[1], inv.inputs[1])
    cb = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sn.outputs[0], cb.inputs[0])
    nt.links.new(inv.outputs[0], cb.inputs[1])
    nt.links.new(sn.outputs[2], cb.inputs[2])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(cb.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return mat
