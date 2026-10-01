"""CardShopKit showcase room: builds /Game/CardShopKit/Maps/L_CSK_Shop from the imported kit (pythonscript commandlet,
-nullrhi). Spec 5.2 L_CSK_Shop: a furnished shop from the J1 shell, 14 x 8 x 3 m: a 10 x 8 sales floor and a 4 x 8 back
room, every case and shelf stocked from its own .csk.json slot grids (slots_ue) and the imported sockets.

Frame (Unreal cm): the room interior is x 0..1400, y 0..800, z 0..300. The back wall is y = 0, the storefront y = 800
(the street is +Y), the back-room partition x = 1000. A fixture "facing +Y" has its customer side toward +Y (yaw 0;
the kit's customer side is Unreal +Y, csk_common), its back on the given back line.

Sales floor: a counter line (two full-vision showcases, the counter with its POS devices, two half-vision showcases)
in front of a staff aisle and a back wall of lit wall cases, oak wall units, towers and the wall slab case; two
gondola runs with end caps; slatwall with hooks and a shelf on the west wall; the box tier and the wire rack on the
partition; card tables and a countertop case by the window; a play area with two tables. Back room: warehouse racks,
workbench, hand truck, bins, cartons. Lights: 600 panels with rect lights, a track with spot heads over the counter
line, pendants over the play tables; sky light + sun through the storefront; an unbound post-process volume holds the
exposure. Cameras CAM_<name> are what csk_shop_capture.py renders.

Every actor is tagged CSK_SHOP; a re-run destroys exactly those. Report: WorkFiles/cardshop/shop/shop.json.
"""
import math
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import csk_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "notes": [], "counts": {}, "missing": []}
EXPOSURE_EV100 = 7.6          # the post-process volume's fixed exposure (min = max EV100), tuned from the captures
SUN_LUX = 20000.0             # daylight outside the storefront (6 lux read as night)
N = {"actors": 0}

FACING_YAW = {"+Y": 0.0, "-Y": 180.0, "+X": -90.0, "-X": 90.0}


# ------------------------------------------------------------------------------------------------ transforms


def V(t):
    return unreal.Vector(float(t[0]), float(t[1]), float(t[2]))


def R(roll=0.0, pitch=0.0, yaw=0.0):
    r = unreal.Rotator()
    r.roll, r.pitch, r.yaw = float(roll), float(pitch), float(yaw)
    return r


def T(loc=(0, 0, 0), rot=(0, 0, 0)):
    """rot is [roll, pitch, yaw] (the .csk.json slots_ue order)."""
    return unreal.Transform(location=V(loc), rotation=R(*rot), scale=V((1, 1, 1)))


def compose(child, parent):
    """World transform of ``child`` (relative) under ``parent``: apply child, then parent."""
    return unreal.MathLibrary.compose_transforms(child, parent)


def rot2(x, y, yaw):
    a = math.radians(yaw)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


CSK = {}


def csk(name):
    if name not in CSK:
        CSK[name] = C.csk(name)
    return CSK[name]


def aabb_ue(name):
    """The mesh's render AABB in its own Unreal frame (cm): Blender mm (x, y, z) -> (x, -y, z) / 10."""
    (x0, y0, z0), (x1, y1, z1) = csk(name)["render_aabb_mm"]
    return (x0 / 10, -y1 / 10, z0 / 10), (x1 / 10, -y0 / 10, z1 / 10)


def at_back(name, facing, bx, by, z=0.0):
    """The transform that puts ``name``'s back-edge midpoint at (bx, by), its customer side toward ``facing``."""
    yaw = FACING_YAW[facing]
    (x0, y0, _), (x1, _, _) = aabb_ue(name)
    ox, oy = rot2((x0 + x1) / 2, y0, yaw)
    return T((bx - ox, by - oy, z), (0, 0, yaw))


def at_min(name, yaw, mx, my, z=0.0):
    """The transform that puts the min corner of ``name``'s turned AABB at (mx, my) (plan view)."""
    (x0, y0, _), (x1, y1, _) = aabb_ue(name)
    pts = [rot2(x, y, yaw) for x in (x0, x1) for y in (y0, y1)]
    return T((mx - min(p[0] for p in pts), my - min(p[1] for p in pts), z), (0, 0, yaw))


# ------------------------------------------------------------------------------------------------ assets / actors

MESH = {}


def mesh(name):
    if name not in MESH:
        m = unreal.load_asset(f"{C.MESH_DEST}/{name}")
        MESH[name] = m if isinstance(m, unreal.StaticMesh) else None
        if MESH[name] is None:
            REP["missing"].append(name)
    return MESH[name]


def socket_T(mesh_name, socket):
    m = mesh(mesh_name)
    s = m.find_socket(socket) if m else None
    if s is None:
        raise RuntimeError(f"{mesh_name} has no socket {socket!r}")
    return unreal.Transform(location=s.get_editor_property("relative_location"),
                            rotation=s.get_editor_property("relative_rotation"), scale=V((1, 1, 1)))


def sockets(mesh_name, prefix):
    return [s["name"] for s in csk(mesh_name)["sockets"] if s["name"].startswith(prefix)]


MI = {}


def mi(name):
    if name not in MI:
        MI[name] = unreal.load_asset(f"{C.MAT_DEST}/{name}")
    return MI[name]


def spawn(mesh_name, t, folder, overrides=None, label=None):
    m = mesh(mesh_name)
    if m is None:
        return None
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, t.translation, R())
    a.static_mesh_component.set_static_mesh(m)
    a.set_actor_transform(t, False, True)
    N["actors"] += 1
    a.set_actor_label(label or f"{mesh_name[7:]}_{N['actors']:04d}")
    a.set_folder_path(folder)
    a.tags = [unreal.Name(C.SHOP_TAG)]
    for slot, name in (overrides or {}).items():
        names = [str(s.get_editor_property("material_slot_name")) for s in m.get_editor_property("static_materials")]
        if slot in names and mi(name) is not None:
            a.static_mesh_component.set_material(names.index(slot), mi(name))
    REP["counts"][mesh_name] = REP["counts"].get(mesh_name, 0) + 1
    return a


def with_parts(mesh_name, t, folder, overrides=None, depth=0):
    """The mesh, its glass (same pivot) and its moving parts on their sockets (closed pose), parts of parts too."""
    a = spawn(mesh_name, t, folder, overrides)
    d = csk(mesh_name)
    if d.get("glass"):
        spawn(d["glass"], t, folder)
    for part in (d.get("parts") or {}).values():
        if isinstance(part, dict) and part.get("mesh") and part.get("socket") and depth < 2:
            try:
                with_parts(part["mesh"], compose(socket_T(mesh_name, part["socket"]), t), folder, depth=depth + 1)
            except RuntimeError as exc:
                REP["notes"].append(str(exc))
    return a


# ------------------------------------------------------------------------------------------------ stock

CARD_MI = [f"MI_CSK_G1_Card_Atlas_{i}" for i in range(6)]
PACK_MI = [f"MI_CSK_G1_Pack_Atlas_{i}" for i in range(3)]
BOX_MI = ["MI_CSK_G1_BoxPrint_Plain", "MI_CSK_G1_BoxPrint_Plain_Lumenfold", "MI_CSK_G1_BoxPrint_Plain_Rimvault"]
BOXL_MI = ["MI_CSK_G1_BoxPrintL", "MI_CSK_G1_BoxPrintL_Lumenfold", "MI_CSK_G1_BoxPrintL_Rimvault"]


def line_of(k):
    """A product line per slot, in runs of three so a shelf reads as blocks of one line."""
    return (k // 3) % 3


def boxes(k):
    return {"M_CSK_BoxPrint": BOX_MI[line_of(k)], "M_CSK_BoxPrintL": BOXL_MI[line_of(k)]}
ITEM = {  # class -> (mesh, overrides for index k)
    "Card": ("SM_CSK_Card_Std", lambda k: {"M_CSK_Card": CARD_MI[k % 6]}),
    "CardProt": ("SM_CSK_TopLoader_35pt_Filled", lambda k: None),
    "Slab": ("SM_CSK_Slab_Std_Filled", lambda k: {"M_CSK_SlabFilled": "MI_CSK_G1_SlabFilled_Atlas"}),
    "Pack": ("SM_CSK_Pack_Std_Sealed", lambda k: {"M_CSK_Pack": PACK_MI[k % 3]}),
    "BoxS": ("SM_CSK_Box_Booster_S_Sealed", boxes),
    "BoxL": ("SM_CSK_Box_Booster_L_Sealed", boxes),
    "BoxC": ("SM_CSK_Box_Collector", boxes),
    "Deck": ("SM_CSK_Deck_Tuck", boxes),
    "Carton": ("SM_CSK_Carton_Box6_Closed", lambda k: None),
    "BoxShipS": ("SM_CSK_Box_Ship_S_Closed", lambda k: None),
    "BoxShipM": ("SM_CSK_Box_Ship_M_Closed", lambda k: None),
    "BoxShipL": ("SM_CSK_Box_Ship_L_Closed", lambda k: None),
}


def fill(fx_T, fx_mesh, level, cls, folder, every=1, limit=None):
    """Stock one level grid of a fixture with its class's item (slots_ue are fixture-local Unreal cm)."""
    lv = next((l for l in csk(fx_mesh).get("levels") or [] if l["socket"] == level), None)
    g = next((x for x in (lv or {}).get("grids", []) if x["class"] == cls), None)
    if g is None:
        REP["notes"].append(f"{fx_mesh}: no {cls} grid on {level}")
        return 0
    item, ov = ITEM[cls]
    n = 0
    for k, s in enumerate(g["slots_ue"]):
        if k % every or (limit is not None and n >= limit):
            continue
        with_parts(item, compose(T(s["loc_cm"], s["rot"]), fx_T), folder, ov(k))
        n += 1
    return n


def box_with_packs(t, folder, k=0):
    """An open booster box (lid folded back as its display header) holding its 36 packs."""
    spawn("SM_CSK_Box_Booster_S", t, folder, {"M_CSK_BoxPrint": BOX_MI[k % 3]})
    part = csk("SM_CSK_Box_Booster_S")["parts"]["Lid"]["open_ue"]
    spawn("SM_CSK_Box_Booster_S_Lid", compose(T(part["loc_cm"], part["rot"]), t), folder, {"M_CSK_BoxPrint": BOX_MI[k % 3]})
    for s in sockets("SM_CSK_Box_Booster_S", "Pack_"):
        spawn("SM_CSK_Pack_Std_Sealed", compose(socket_T("SM_CSK_Box_Booster_S", s), t), folder,
              {"M_CSK_Pack": PACK_MI[k % 3]})


def hang(hook_T, hook_mesh, item, folder, n=None, overrides=None):
    """Items hung plumb along a hook's arm: item world = inverse(item Hang socket) x hook point x hook."""
    h = csk(hook_mesh)["hang"]
    start = socket_T(hook_mesh, h["socket"]).translation
    ax = h["axis"]
    axis = (ax[0], -ax[1], ax[2])                      # Blender -> Unreal direction
    pitch = csk(item)["hang"]["pitch_mm"] / 10.0
    run = h["run_mm"] / 10.0
    count = int(run // pitch) if n is None else min(n, int(run // pitch))
    inv = socket_T(item, "Hang").inverse()
    for k in range(count):
        d = pitch * (k + 0.5)
        p = (start.x + axis[0] * d, start.y + axis[1] * d, start.z + axis[2] * d)
        spawn(item, compose(compose(inv, T(p)), hook_T), folder, overrides)


# ------------------------------------------------------------------------------------------------ the room


def shell():
    f = "Shop/Shell"
    back = ["Wall"] * 7
    front = ["Wall_Window", "Wall_Window", "Wall_Door", "Wall_Window", "Wall_Window", "Wall", "Wall"]
    for i, kind in enumerate(back):                                    # back wall, shop face +Y at y = 0
        spawn(f"SM_CSK_Shell_{kind}_2000", T((200 * i, 0, 0), (0, 0, 0)), f)
    door_T = None
    for i, kind in enumerate(front):                                   # storefront, shop face -Y at y = 800
        t = T((200 * i + 200, 800, 0), (0, 0, 180))
        spawn(f"SM_CSK_Shell_{kind}_2000", t, f)
        if kind == "Wall_Window":
            spawn("SM_CSK_Shell_Wall_Window_2000_Glass", t, f)
        if kind == "Wall_Door":
            door_T = compose(socket_T("SM_CSK_Shell_Wall_Door_2000", "Mount_DoorFrame"), t)
    for j in range(4):
        spawn("SM_CSK_Shell_Wall_2000", T((0, 200 * j + 200, 0), (0, 0, -90)), f)      # west, facing +X
        spawn("SM_CSK_Shell_Wall_2000", T((1400, 200 * j, 0), (0, 0, 90)), f)         # east, facing -X
        kind = "Wall_Door" if j == 1 else "Wall"                                        # partition, faces the floor
        spawn(f"SM_CSK_Shell_{kind}_2000", T((1000, 200 * j, 0), (0, 0, 90)), f)
    for i in range(7):
        for j in range(4):
            spawn("SM_CSK_Shell_Floor_2000", at_min("SM_CSK_Shell_Floor_2000", 0, 200 * i, 200 * j, 0.0), f)
            spawn("SM_CSK_Shell_Ceiling_2000", at_min("SM_CSK_Shell_Ceiling_2000", 0, 200 * i, 200 * j, 300.0), f)
    with_parts("SM_CSK_Door_Entry_Frame", door_T, "Shop/Entry")
    # the storefront sign on the street face above the door, the open/closed sign in the window beside it
    spawn("SM_CSK_Sign_Storefront", at_back("SM_CSK_Sign_Storefront", "+Y", door_T.translation.x, 816.0, 262.0),
          "Shop/Entry")
    with_parts("SM_CSK_Sign_OpenClosed", T((330, 795, 235), (0, 0, 180)), "Shop/Entry")
    ground = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V((700, 400, -2.5)), R())
    ground.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
    ground.set_actor_scale3d(V((120, 120, 1)))
    ground.set_actor_label("Street_Ground")
    ground.set_folder_path(f)
    ground.tags = [unreal.Name(C.SHOP_TAG)]
    return door_T


def back_wall():
    """Behind the staff aisle, left to right: lit wall case, oak wall unit, tower, wall slab case, oak wall unit, lit
    wall case, tower, a poster."""
    f = "Shop/BackWall"
    x = 100.0
    for name, kind in (("SM_CSK_Showcase_Wall_1016", "wall"), ("SM_CSK_WallUnit_Oak", "oak"),
                       ("SM_CSK_Showcase_Tower", "tower"), ("SM_CSK_Case_WallSlab", "slab"),
                       ("SM_CSK_WallUnit_Oak", "oak"), ("SM_CSK_Showcase_Wall_1016", "wall"),
                       ("SM_CSK_Showcase_Tower", "tower")):
        (x0, _, _), (x1, _, _) = aabb_ue(name)
        w = x1 - x0
        cx = x + w / 2
        if kind == "slab":
            t = at_back(name, "+Y", cx, 0.0, 150.0)          # wall-mounted, its pivot the back-face centre
        else:
            t = at_back(name, "+Y", cx, 0.0)
        with_parts(name, t, f)
        if kind == "wall":
            for lvl, cls in zip(["Level_L1", "Level_L2", "Level_L3", "Level_L4", "Level_L5"],
                                ["BoxS", "Deck", "Pack", "CardProt", "Slab"]):
                fill(t, name, lvl, cls, f)
        elif kind == "oak":
            for lvl, cls in zip(["Level_L1", "Level_L2", "Level_L3", "Level_L4"], ["BoxS", "BoxS", "Deck", "Pack"]):
                fill(t, name, lvl, cls, f)
        elif kind == "tower":
            for lvl, cls in zip(["Level_L1", "Level_L2", "Level_L3", "Level_L4", "Level_L5"],
                                ["BoxS", "Deck", "Slab", "CardProt", "Slab"]):
                fill(t, name, lvl, cls, f)
        elif kind == "slab":
            for s in sockets(name, "Slot_R"):
                spawn("SM_CSK_Slab_Std_Filled", compose(socket_T(name, s), t), f,
                      {"M_CSK_SlabFilled": "MI_CSK_G1_SlabFilled_Atlas"})
        x += w + 8.0
    spawn("SM_CSK_Poster_A1", at_back("SM_CSK_Poster_A1", "+Y", 955.0, 0.0, 175.0), f)


def counter_line():
    """The customer faces of the line are flush at y = 305: full, counter, full, half, half."""
    f = "Shop/CounterLine"
    front = 305.0
    x = 60.0
    out = {}
    for name in ("SM_CSK_Showcase_Full_1778", "SM_CSK_Counter_1397", "SM_CSK_Showcase_Full_1778",
                 "SM_CSK_Showcase_Half_1778", "SM_CSK_Showcase_Half_1219"):
        (x0, y0, _), (x1, y1, _) = aabb_ue(name)
        t = at_back(name, "+Y", x + (x1 - x0) / 2, front - (y1 - y0))
        with_parts(name, t, f)
        out.setdefault(name, []).append(t)
        x += (x1 - x0) + 6.0
    f1, f2 = out["SM_CSK_Showcase_Full_1778"]
    fill(f1, "SM_CSK_Showcase_Full_1778", "Level_S2", "CardProt", f)
    fill(f1, "SM_CSK_Showcase_Full_1778", "Level_S1", "Slab", f)
    deck = next(l for l in csk("SM_CSK_Showcase_Full_1778")["levels"] if l["socket"] == "Level_Deck")
    boxes = next(g for g in deck["grids"] if g["class"] == "BoxS")["slots_ue"]
    for k, s in enumerate(boxes[:4]):                    # the front row: open boxes of packs
        box_with_packs(compose(T(s["loc_cm"], s["rot"]), f1), f, k)
    fill(f2, "SM_CSK_Showcase_Full_1778", "Level_S2", "Card", f)
    fill(f2, "SM_CSK_Showcase_Full_1778", "Level_S1", "Slab", f)
    fill(f2, "SM_CSK_Showcase_Full_1778", "Level_Deck", "Deck", f)
    h1 = out["SM_CSK_Showcase_Half_1778"][0]
    fill(h1, "SM_CSK_Showcase_Half_1778", "Level_S1", "CardProt", f)
    fill(h1, "SM_CSK_Showcase_Half_1778", "Level_Deck", "Slab", f)
    h2 = out["SM_CSK_Showcase_Half_1219"][0]
    fill(h2, "SM_CSK_Showcase_Half_1219", "Level_S1", "Pack", f)
    fill(h2, "SM_CSK_Showcase_Half_1219", "Level_Deck", "BoxS", f)
    # the counter's devices on their sockets
    ct = out["SM_CSK_Counter_1397"][0]
    for sock, dev in (("POS", "SM_CSK_POS_Screen"), ("Printer", "SM_CSK_Printer_Receipt"),
                      ("Scanner", "SM_CSK_Scanner_Cradle"), ("Terminal", "SM_CSK_Terminal_Card"),
                      ("PriceGun", "SM_CSK_PriceGun"), ("Phone", "SM_CSK_Phone"), ("Drawer", "SM_CSK_CashDrawer"),
                      ("Bag", "SM_CSK_Bag_Paper")):
        with_parts(dev, compose(socket_T("SM_CSK_Counter_1397", sock), ct), f)
    sc = compose(socket_T("SM_CSK_Counter_1397", "Scanner"), ct)
    spawn("SM_CSK_Scanner", compose(socket_T("SM_CSK_Scanner_Cradle", "Scanner"), sc), f)
    return out


def gondolas():
    """Two runs across the floor: end cap, two doubles, end cap; three 406 shelves a side on the doubles."""
    f = "Shop/Gondolas"
    (gx0, gy0, _), (gx1, gy1, _) = aabb_ue("SM_CSK_Gondola_Double_1372")
    dw, dd = gx1 - gx0, gy1 - gy0
    yc = 470.0                                             # the run's centre line
    x = 190.0
    (_, ey0, _), (_, ey1, _) = aabb_ue("SM_CSK_Gondola_EndCap_1372")
    ed = ey1 - ey0
    with_parts("SM_CSK_Gondola_EndCap_1372", at_back("SM_CSK_Gondola_EndCap_1372", "-X", x + ed, yc), f)
    fill(at_back("SM_CSK_Gondola_EndCap_1372", "-X", x + ed, yc), "SM_CSK_Gondola_EndCap_1372", "Level_Deck", "BoxL", f)
    x += ed
    mix = [("BoxS", "Deck", "Pack"), ("BoxC", "BoxS", "Deck")]
    for i in range(2):
        t = at_back("SM_CSK_Gondola_Double_1372", "+Y", x + dw / 2, yc - dd / 2)
        with_parts("SM_CSK_Gondola_Double_1372", t, f)
        fill(t, "SM_CSK_Gondola_Double_1372", "Level_DeckF", "BoxL", f)
        fill(t, "SM_CSK_Gondola_Double_1372", "Level_DeckB", "BoxL", f)
        for side in ("F", "B"):
            for mount, cls in zip(("03", "06", "09"), mix[i]):
                st = compose(socket_T("SM_CSK_Gondola_Double_1372", f"Mount_{side}_{mount}"), t)
                with_parts("SM_CSK_Gondola_Shelf_406", st, f)
                fill(st, "SM_CSK_Gondola_Shelf_406", "Level_S1", cls, f)
                for s in sockets("SM_CSK_Gondola_Shelf_406", "PriceTag_S1_")[::2]:
                    spawn("SM_CSK_PriceTag_Shelf", compose(socket_T("SM_CSK_Gondola_Shelf_406", s), st), f)
        x += dw
    t = at_back("SM_CSK_Gondola_EndCap_1372", "+X", x, yc)
    with_parts("SM_CSK_Gondola_EndCap_1372", t, f)
    fill(t, "SM_CSK_Gondola_EndCap_1372", "Level_Deck", "BoxC", f)


def west_wall():
    """Two 2000 slatwall panels on the west wall: rows of hooks with hang packs, and a shelf of deck boxes."""
    f = "Shop/Slatwall"
    hang_items = ["SM_CSK_Blister_Pack", "SM_CSK_Retail_SleeveBox100", "SM_CSK_Retail_TopLoaderPack25",
                  "SM_CSK_Retail_PennyPack100", "SM_CSK_Retail_DiceClam"]
    k = 0
    for j, b in enumerate((330.0, 540.0)):
        t = T((0, b + 200.0, 0), (0, 0, -90))             # facing +X; its left end (pivot) at the larger y
        with_parts("SM_CSK_Slatwall_2000x2400", t, f)
        for row, groove in enumerate(("Groove_24", "Groove_19", "Groove_14")):
            gt = compose(socket_T("SM_CSK_Slatwall_2000x2400", groove), t)
            for dx in (30.0, 70.0, 110.0, 150.0):
                ht = compose(T((dx, 0, 0)), gt)
                with_parts("SM_CSK_Hook_Slat_203", ht, f)
                item = hang_items[k % len(hang_items)]
                k += 1
                ov = {"M_CSK_Pack": PACK_MI[k % 3]} if item == "SM_CSK_Blister_Pack" else None
                hang(ht, "SM_CSK_Hook_Slat_203", item, f, n=5, overrides=ov)
        st = compose(T((100.0, 0, 0)), compose(socket_T("SM_CSK_Slatwall_2000x2400", "Groove_09"), t))
        with_parts("SM_CSK_Shelf_Slat_1000", st, f)
        fill(st, "SM_CSK_Shelf_Slat_1000", "Level_S1", "Deck" if j == 0 else "BoxC", f)


def partition():
    """On the partition's sales face (x = 1000, facing -X): the box tier shelf, the wire rack, two posters."""
    f = "Shop/Partition"
    t = at_back("SM_CSK_Shelf_BoxTier_1219", "-X", 1000.0, 395.0)
    with_parts("SM_CSK_Shelf_BoxTier_1219", t, f)
    for lvl, cls in zip(["Level_T1", "Level_T2", "Level_T3", "Level_T4"], ["BoxL", "BoxS", "BoxS", "BoxC"]):
        fill(t, "SM_CSK_Shelf_BoxTier_1219", lvl, cls, f)
    t = at_back("SM_CSK_Rack_Wire_914", "-X", 1000.0, 520.0)
    with_parts("SM_CSK_Rack_Wire_914", t, f)
    for lvl, cls in zip(["Level_L1", "Level_L2", "Level_L3", "Level_L4", "Level_L5"],
                        ["BoxL", "BoxC", "BoxS", "Deck", "Pack"]):
        fill(t, "SM_CSK_Rack_Wire_914", lvl, cls, f)
    spawn("SM_CSK_Poster_A1", at_back("SM_CSK_Poster_A1", "-X", 1000.0, 640.0, 175.0), f)
    spawn("SM_CSK_Poster_A2", at_back("SM_CSK_Poster_A2", "-X", 1000.0, 735.0, 170.0), f)


def front_floor():
    """By the storefront: two card tables and a countertop case on a small table left of the door; the play area
    (a 4-seat and a 2-seat table with chairs, mats, deck boxes and dice) right of it."""
    f = "Shop/Front"
    for i, cx in enumerate((95.0, 185.0)):
        t = at_back("SM_CSK_CardTable_10", "-Y", cx, 760.0)
        with_parts("SM_CSK_CardTable_10", t, f)
        for k, s in enumerate(sockets("SM_CSK_CardTable_10", "Slot_")):
            spawn("SM_CSK_Card_Std", compose(socket_T("SM_CSK_CardTable_10", s), t), f,
                  {"M_CSK_Card": CARD_MI[(k + i) % 6]})
    t = at_back("SM_CSK_Table_Play_2", "-Y", 300.0, 765.0)
    with_parts("SM_CSK_Table_Play_2", t, f)
    top = aabb_ue("SM_CSK_Table_Play_2")[1][2]
    ct = compose(T((0, 0, top)), t)
    with_parts("SM_CSK_Case_Counter_900", ct, f)
    fill(ct, "SM_CSK_Case_Counter_900", "Level_Deck", "Slab", f)
    play = "Shop/PlayArea"
    for name, cx in (("SM_CSK_Table_Play_4", 700.0), ("SM_CSK_Table_Play_2", 890.0)):
        t = T((cx, 650.0, 0), (0, 0, 0))
        with_parts(name, t, play)
        for s in sockets(name, "Chair_"):
            with_parts("SM_CSK_Chair_Folding", compose(socket_T(name, s), t), play)
        for k, s in enumerate(sockets(name, "Mat_")):
            spawn("SM_CSK_Playmat_Flat", compose(socket_T(name, s), t), play)
        for k, s in enumerate(sockets(name, "Deck_")):
            dt = compose(socket_T(name, s), t)
            with_parts("SM_CSK_DeckBox", dt, play)
            spawn("SM_CSK_Die_D20", compose(T((9.0, 0.0, 0.0)), dt), play)
            spawn("SM_CSK_Die_D6", compose(T((9.0, 4.0, 0.0)), dt), play)


def back_room():
    f = "Shop/BackRoom"
    for i, yb in enumerate((15.0, 210.0)):
        t = at_back("SM_CSK_Rack_Warehouse_1829", "-X", 1400.0, yb + 91.5)
        with_parts("SM_CSK_Rack_Warehouse_1829", t, f)
        for lvl, cls in zip(["Level_L1", "Level_L2", "Level_L3", "Level_L4", "Level_L5"],
                            (["BoxShipL", "Carton", "BoxShipM", "Carton", "BoxShipS"],
                             ["Carton", "BoxShipS", "Carton", "BoxShipM", "Carton"])[i]):
            fill(t, "SM_CSK_Rack_Warehouse_1829", lvl, cls, f)
    t = at_back("SM_CSK_Workbench_1524", "-Y", 1290.0, 800.0)
    with_parts("SM_CSK_Workbench_1524", t, f)
    for sock, item in (("Work", "SM_CSK_Mailer_L_Open"), ("Tool_01", "SM_CSK_TapeGun"), ("Tool_02", "SM_CSK_Mailer_S"),
                       ("Tool_03", "SM_CSK_Box_GradeReturn"), ("BulkOut", "SM_CSK_Box_Row_800")):
        with_parts(item, compose(socket_T("SM_CSK_Workbench_1524", sock), t), f)
    ht = T((1120.0, 560.0, 0), (0, 0, 90))
    with_parts("SM_CSK_HandTruck", ht, f)
    nose = compose(socket_T("SM_CSK_HandTruck", "Nose"), ht)
    h = aabb_ue("SM_CSK_Carton_Box6_Closed")[1][2]
    for k in range(3):
        spawn("SM_CSK_Carton_Box6_Closed", compose(T((0, 0, h * k)), nose), f)
    with_parts("SM_CSK_TrashCan", T((1035.0, 770.0, 0), (0, 0, 180)), f)
    spawn("SM_CSK_TrashBag_Full", T((1090.0, 760.0, 0), (0, 0, 25)), f)
    ot = T((1150.0, 130.0, 0), (0, 0, 10))
    spawn("SM_CSK_Carton_Box6_Open", ot, f)
    for s in sockets("SM_CSK_Carton_Box6_Open", "Box_"):
        spawn("SM_CSK_Box_Booster_S_Sealed", compose(socket_T("SM_CSK_Carton_Box6_Open", s), ot), f)
    spawn("SM_CSK_Box_Ship_M_Open", T((1250.0, 470.0, 0), (0, 0, -15)), f)
    spawn("SM_CSK_Box_Ship_Flat", T((1180.0, 440.0, 0.1), (0, 0, 80)), f)
    mt = T((1060.0, 90.0, 0), (0, 0, 90))
    with_parts("SM_CSK_Box_Monster_5000", mt, f)


def lights():
    f = "Shop/Lights"
    out = {"rect": 0, "spot": 0, "point": 0}

    def light(cls, loc, rot, lumens, **kw):
        a = EAS.spawn_actor_from_class(cls, V(loc), rot)
        a.set_folder_path(f)
        a.tags = [unreal.Name(C.SHOP_TAG)]
        lc = a.get_component_by_class(unreal.LightComponent)
        lc.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
        lc.set_editor_property("intensity", float(lumens))
        lc.set_editor_property("use_temperature", True)
        lc.set_editor_property("temperature", kw.pop("kelvin", 4000.0))
        for k, v in kw.items():
            lc.set_editor_property(k, v)
        return a
    down = R(0, -90, 0)
    PANEL = {"M_CSK_LED": "MI_CSK_G1_LED_Panel"}
    for cx in (130.0, 380.0, 620.0, 870.0):                # 600 panels over the sales floor
        for cy in (150.0, 440.0, 690.0):
            spawn("SM_CSK_Light_Panel600", T((cx, cy, 300.0)), f, PANEL)
            light(unreal.RectLight, (cx, cy, 298.6), down, 3600, source_width=58.0, source_height=58.0,
                  barn_door_length=0.0, attenuation_radius=1500.0)
            out["rect"] += 1
    for cx, cy in ((1200.0, 200.0), (1200.0, 600.0)):     # back room
        spawn("SM_CSK_Light_Panel600", T((cx, cy, 300.0)), f, PANEL)
        light(unreal.RectLight, (cx, cy, 298.6), down, 3000, source_width=58.0, source_height=58.0,
              barn_door_length=0.0, attenuation_radius=1200.0)
        out["rect"] += 1
    tt = T((520.0, 335.0, 300.0))                          # track over the counter line, heads aimed at the cases
    spawn("SM_CSK_Light_Track2000", tt, f)
    for s in sockets("SM_CSK_Light_Track2000", "Head_"):
        ht = compose(T((0, 0, 0), (0, 0, 180)), compose(socket_T("SM_CSK_Light_Track2000", s), tt))
        with_parts("SM_CSK_Light_TrackHead", ht, f)
        p = ht.translation
        light(unreal.SpotLight, (p.x, p.y - 6.0, p.z - 12.0), R(0, -62, -90), 900, inner_cone_angle=14.0,
              outer_cone_angle=24.0, attenuation_radius=800.0, kelvin=3500.0)
        out["spot"] += 1
    for cx in (700.0, 890.0):                              # pendants over the play tables
        spawn("SM_CSK_Light_Pendant", T((cx, 650.0, 300.0)), f)
        light(unreal.PointLight, (cx, 650.0, 172.0), R(), 1200, source_radius=8.0, attenuation_radius=600.0,
              kelvin=3000.0)
        out["point"] += 1
    spawn("SM_CSK_Sign_Hanging", at_back("SM_CSK_Sign_Hanging", "+Y", 520.0, 372.0, 300.0), f)
    # sun + sky through the storefront, and the exposure
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, V((700, 1200, 800)), R(0, -38, -118))
    sky = EAS.spawn_actor_from_class(unreal.SkyLight, V((700, 400, 500)), R())
    atm = EAS.spawn_actor_from_class(unreal.SkyAtmosphere, V((0, 0, 0)), R())
    for a in (sun, sky, atm):
        a.set_folder_path("Shop/Sky")
        a.tags = [unreal.Name(C.SHOP_TAG)]
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_editor_property("intensity", SUN_LUX)
    ppv = EAS.spawn_actor_from_class(unreal.PostProcessVolume, V((700, 400, 150)), R())
    ppv.set_folder_path("Shop/Sky")
    ppv.tags = [unreal.Name(C.SHOP_TAG)]
    ppv.set_actor_label("PPV_Exposure")
    ppv.set_editor_property("unbound", True)
    s = ppv.get_editor_property("settings")
    for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM),
                 ("override_auto_exposure_min_brightness", True), ("auto_exposure_min_brightness", EXPOSURE_EV100),
                 ("override_auto_exposure_max_brightness", True), ("auto_exposure_max_brightness", EXPOSURE_EV100),
                 ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.0)):
        s.set_editor_property(k, v)
    ppv.set_editor_property("settings", s)
    return out


CAMERAS = {  # name: (location cm, look-at cm, horizontal FOV deg)
    "C1_Entrance": ((490, 760, 168), (470, 160, 95), 78),
    "C2_Counter": ((420, 470, 158), (330, 270, 100), 62),
    "C3_Staff": ((520, 60, 166), (560, 700, 95), 82),
    "C4_Showcase": ((170, 390, 128), (160, 280, 78), 52),
    "C5_Aisle": ((110, 610, 158), (470, 470, 90), 72),
    "C6_Play": ((560, 540, 168), (800, 670, 72), 72),
    "C7_BackRoom": ((1030, 110, 172), (1320, 520, 90), 84),
    "C8_Overview": ((40, 785, 282), (620, 230, 55), 88),
    "C9_Slatwall": ((190, 430, 150), (0, 540, 135), 72),
    "C10_BackWall": ((560, 215, 150), (430, 0, 140), 74),
}


DIAG_CAMERAS = {  # CSK_DIAG=1 adds these (lighting checks, not showcase shots)
    "D1_Ceiling": ((720, 400, 150), (725, 400, 300), 90),
    "D2_Street": ((500, 1500, 170), (500, 800, 150), 70),
}


def cameras():
    out = {}
    cams = dict(CAMERAS, **(DIAG_CAMERAS if os.environ.get("CSK_DIAG") == "1" else {}))
    for name, (loc, look, fov) in cams.items():
        dx, dy, dz = (look[i] - loc[i] for i in range(3))
        yaw = math.degrees(math.atan2(dy, dx))
        pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
        a = EAS.spawn_actor_from_class(unreal.CameraActor, V(loc), R(0, pitch, yaw))
        a.set_actor_label("CAM_" + name)
        a.set_folder_path("Shop/Cameras")
        a.tags = [unreal.Name(C.SHOP_TAG)]
        a.get_component_by_class(unreal.CameraComponent).set_editor_property("field_of_view", float(fov))
        out[name] = {"loc": list(loc), "look": list(look), "fov": fov}
    return out


# ------------------------------------------------------------------------------------------------ main


def open_level(path):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if EAL.does_asset_exist(path):
        ok = les.load_level(path)
    else:
        try:
            ok = les.new_level(path, False)
        except TypeError:
            ok = les.new_level(path)
    removed = 0
    for a in EAS.get_all_level_actors():
        if unreal.Name(C.SHOP_TAG) in list(a.tags):
            EAS.destroy_actor(a)
            removed += 1
    return {"open": bool(ok), "managed_removed": removed}


def save_level(path):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    try:
        if les.save_current_level():
            return True
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"save_current_level: {exc}")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    return bool(unreal.EditorLoadingAndSavingUtils.save_map(world, path))


def main():
    t0 = time.time()
    try:
        REP["level"] = open_level(C.SHOP_LEVEL)
        for name, fn in (("shell", shell), ("back_wall", back_wall), ("counter_line", counter_line),
                         ("gondolas", gondolas), ("west_wall", west_wall), ("partition", partition),
                         ("front_floor", front_floor), ("back_room", back_room), ("lights", lights),
                         ("cameras", cameras)):
            n0 = N["actors"]
            try:
                res = fn()
                REP[name] = {"actors": N["actors"] - n0, "result": res if name in ("lights", "cameras") else None}
            except Exception:  # noqa: BLE001      # one failed zone must not lose the rest of the room
                REP[name] = {"error": traceback.format_exc()[-2500:]}
        REP["actors"] = N["actors"]
        REP["saved"] = save_level(C.SHOP_LEVEL)
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
    errs = [k for k, v in REP.items() if isinstance(v, dict) and v.get("error")] + (["error"] if "error" in REP else [])
    REP["errors"] = errs
    REP["passed"] = bool(REP.get("saved")) and not errs and not REP["missing"]
    REP["sec"] = round(time.time() - t0, 1)
    C.write_json(C.SHOP_OUT / "shop.json", REP)
    unreal.log(f"CSK_STEP_DONE shop passed={REP['passed']} actors={N['actors']}")


main()
