"""KIT 1 review renders (Cycles, headless) from Assets/Dojo/DojoKit1.blend (read-only: nothing is saved).

--what wall     model-sheet views of the wall: front / side / top ortho of a straight run (End + 2 m + End), 3/4
                perspective, outside corner 3/4 + top, inside corner (valley) 3/4, a section cut (boolean copy)
--what gate     outside elevation (doors closed), side elevation (the wall passing through), top view (doors open),
                3/4 from outside
--what variants the assembled 2.0 / 2.5 / 3.0 m wall variants side by side (front ortho)
--what beauty   sunset shots in context on the grey-box: gate from the courtyard, along the south wall, reference-2
                framing through the gate
Sheet views render on a transparent film with a shadow catcher; compose_kit1.py lays them out on the reference sheets'
light grey (#A0A0A0) with the 1.8 m silhouettes. Every ortho view writes its scale (px per m) and ground row to
views.json so the silhouettes are exactly 1.8 m.

Run: blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/render_kit1.py -- --what wall
     [--samples 128] [--scale 1.0] [--tag r1]
Out: WorkFiles/dojo/build/renders/kit1/<tag>/
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(bpy.data.filepath).resolve().parents[2]
WORK = ROOT / "WorkFiles" / "dojo" / "build"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


WHAT = arg("--what", "wall")
SAMPLES = int(arg("--samples", "128"))
SCALE = float(arg("--scale", "1.0"))
TAG = arg("--tag", "r1")
OUT = (WORK / "renders" / "kit1" / TAG).resolve()
OUT.mkdir(parents=True, exist_ok=True)
L = json.loads((WORK / "layout.json").read_text(encoding="utf-8"))
K = L["kit1"]
sc = bpy.context.scene
KIT = {o.name: o for o in bpy.data.collections["Kit"].objects if o.type == "MESH" and not o.name.startswith("UCX_")}
ZB = K["body_top_z"]
FH = K["footing_h"]
VIEWS = {}


# ------------------------------------------------------------------------------------------------ helpers
def setup_cycles():
    sc.render.engine = "CYCLES"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    try:
        sc.cycles.device = "GPU"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
    except Exception:  # noqa: BLE001
        pass
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"


def coll(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        sc.collection.children.link(c)
    return c


def inst(piece, loc, rot=0.0, c=None, name=None):
    o = bpy.data.objects.new(name or f"{piece}__view", KIT[piece].data)
    o["sheet"] = True
    o.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    (c or coll("Sheet")).objects.link(o)
    return o


def wall_module(L_, x0, y_inner, rot, key="T200", c=None, kind="straight", flip=False):
    """Footing + body + cap of one module along X (rot 0: inner face at y_inner) or turned."""
    parts = {"straight": (f"SM_DK_WallFooting_{L_}m", f"SM_DK_WallBody_{L_}m_{key}", f"SM_DK_WallCap_{L_}m"),
             "end": ("SM_DK_WallFooting_End", f"SM_DK_WallBody_1m_{key}", "SM_DK_WallCap_End")}[kind]
    R = Matrix.Rotation(math.radians(rot), 4, "Z")
    base = Vector((x0, y_inner, 0.0))
    if flip:   # turned 180 about the module centre: pivot at local (L, -1)
        base = base + R @ Vector((L_, -1.0, 0.0))
        rot = rot + 180.0
    out = []
    for p, z in zip(parts, (0.0, FH, ZB[key])):
        out.append(inst(p, base + Vector((0, 0, z)), rot, c))
    return out


def ortho_cam(name, centre, forward, up, width_m, w, h):
    cam = bpy.data.cameras.new(name)
    cam.type = "ORTHO"
    cam.ortho_scale = width_m
    cam.sensor_fit = "HORIZONTAL"
    cam.clip_start = 0.1
    cam.clip_end = 400.0
    o = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(o)
    f = Vector(forward).normalized()
    o.matrix_world = Matrix.Translation(Vector(centre) - f * 60.0) @ f.to_track_quat("-Z", "Y").to_matrix().to_4x4()
    return o


def persp_cam(name, loc, look, lens=50.0, shift_y=0.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = 36.0
    cam.clip_start = 0.05
    cam.clip_end = 600.0
    cam.shift_y = shift_y
    o = bpy.data.objects.new(name, cam)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def render(cam, name, w, h):
    sc.camera = cam
    sc.render.resolution_x = int(w * SCALE)
    sc.render.resolution_y = int(h * SCALE)
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc.render.filepath)


def ortho_view(name, centre, forward, width_m, w, h, meta=None, clip_above=None):
    """Ortho render; records the scale and where world points land. forward: '+y' | '-x' | '-z' (etc.)."""
    fwd = {"+y": (0, 1, 0), "-y": (0, -1, 0), "+x": (1, 0, 0), "-x": (-1, 0, 0), "-z": (0, 0, -1)}[forward]
    cam = ortho_cam("CAM_" + name, centre, fwd, (0, 0, 1), width_m, w, h)
    if clip_above is not None:    # a plan cut: the camera sits 60 m above the centre and clips everything above
        cam.data.clip_start = 60.0 - (clip_above - centre[2])
    for c in CATCHERS:            # elevations and plans: no ground shadow (the sheets' orthographic views are clean)
        c.hide_render = True
    render(cam, name, w, h)
    for c in CATCHERS:
        c.hide_render = False
    ppm = w * SCALE / width_m
    VIEWS[name] = {"ppm": ppm, "w": int(w * SCALE), "h": int(h * SCALE), "centre": list(centre), "forward": forward,
                   **(meta or {})}
    bpy.data.objects.remove(cam, do_unlink=True)


def hide_assembly(hide=True):
    for o in bpy.data.collections["Assembly"].objects:
        o.hide_render = hide or o.name.startswith("SM_DGB_Boundary_1v1__")


# ------------------------------------------------------------------------------------------------ sheet look
def sheet_look():
    setup_cycles()
    sc.render.film_transparent = True
    world = bpy.data.worlds.new("SheetGrey")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.62, 0.62, 0.62, 1.0)
    bg.inputs["Strength"].default_value = 0.75
    sc.world = world
    lt = bpy.data.lights.new("Key", "SUN")
    lt.energy = 3.2
    lt.angle = math.radians(22.0)
    lt.color = (1.0, 0.98, 0.95)
    ko = bpy.data.objects.new("Key", lt)
    sc.collection.objects.link(ko)
    ko.rotation_euler = Vector((0.45, 0.75, -0.62)).to_track_quat("-Z", "Y").to_euler()   # travel dir: from front-left
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Base Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = 0.25


CATCHERS = []


def shadow_catcher(cx, cy, size=80.0):
    me = bpy.data.meshes.new("Catcher")
    h = size / 2
    me.from_pydata([(cx - h, cy - h, -0.001), (cx + h, cy - h, -0.001), (cx + h, cy + h, -0.001), (cx - h, cy + h, -0.001)],
                   [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("Catcher", me)
    coll("Sheet").objects.link(o)
    o.is_shadow_catcher = True
    CATCHERS.append(o)
    return o


# ------------------------------------------------------------------------------------------------ WALL sheet
# r2 (the judge: the open wall end had placeholder surfaces: a flat 2D crazy-paving pattern on the gable triangle and
# the footing end, a flat speckle on the plaster end, pillow stones poking past the end face): the section is now
# MODELLED. The kit meshes are cut at x_cut (every stone, block, timber and tile shows its own cut in its own library
# material, UV-mapped on the cut plane); behind the cut, the footing's rubble core is real packed stones (the library
# GraniteRubble texture's own cells, hewn, 1-1.5 cm proud) in a recessed earth mortar; the plaster body shows a 25 mm
# plaster skin round a rammed-earth core laid in 9-14 cm lifts (real stepped layers); the cap's clay bed under the tiles
# the same lifts. Render-only: this is the sheet's construction view, not a kit piece.
sys.path.insert(0, str(ROOT / "Scripts" / "dojo"))
import kit1_geo as G  # noqa: E402
import random  # noqa: E402

LIB_EP, LIB_RB, LIB_GR, LIB_TA, LIB_TE = ("M_DJ_PlasterEarth", "M_DJ_GraniteRubble", "M_DJ_Granite",
                                          "M_DJ_TimberAged", "M_DJ_TimberAgedEnd")


def section_earth():
    """Render-only: the rammed-earth core = the library earthen plaster's maps, darker and browner (a copy with a
    multiply; the section view only)."""
    m = bpy.data.materials.get("M_DK_SectionEarth")
    if m:
        return m
    m = bpy.data.materials[LIB_EP].copy()
    m.name = "M_DK_SectionEarth"
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    lk = bsdf.inputs["Base Color"].links[0]
    src = lk.from_socket
    nt.links.remove(lk)
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    nt.links.new(src, mul.inputs["A"])
    mul.inputs["B"].default_value = (0.36, 0.29, 0.21, 1.0)
    nt.links.new(mul.outputs["Result"], bsdf.inputs["Base Color"])
    return m


def geo_to_object(g, name, x_cut, mats):
    """A kit1_geo Geo (built in section-plane coordinates) -> a mesh object with UV0 from the Geo's explicit UVs or
    the library box orientation (+X face: (y, z) / 4)."""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UV0")
    vs = [bm.verts.new(p) for p in g.v]
    names = []
    smooth = []
    for fi, f in enumerate(g.f):
        try:
            face = bm.faces.new([vs[i] for i in f])
        except ValueError:
            continue
        smooth.append(bool(g.fsm[fi]) if fi < len(g.fsm) else False)
        m = g.fm[fi]
        if m not in names:
            names.append(m)
        face.material_index = names.index(m)
        face.normal_update()
        rr = random.Random(g.fp[fi] * 31 + 7)
        ou, ov = (0.0, 0.0) if m == "M_DK_SectionEarth" else (rr.random(), rr.random())
        n = face.normal
        for loop, vi in zip(face.loops, f):
            if vi in g.vuv:
                loop[uvl].uv = g.vuv[vi]
                continue
            co = loop.vert.co
            ax = max(range(3), key=lambda k: abs(n[k]))
            s = 1.0 if n[ax] >= 0 else -1.0
            u, v = ((s * co.y, co.z) if ax == 0 else (-s * co.x, co.z) if ax == 1 else (co.x, s * co.y))
            loop[uvl].uv = (u / 4.0 + ou, v / 4.0 + ov)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", smooth)
    for m in names:
        me.materials.append(mats[m])
    o = bpy.data.objects.new(name, me)
    coll("Sheet").objects.link(o)
    return o


def earth_face(g, poly, x_cut, rng, step=0.02):
    """The rammed-earth core on the cut: a lumpy surface (up to 1 cm relief at 3-8 cm, grit at 1 cm) over the convex
    polygon, clipped exactly to it (grid cells clipped by the polygon's edges), the lift lines every 9-14 cm as wavy
    3 mm steps, smooth-shaded; small granite pebbles set in it (1.5-3 cm, 3-6 mm proud); a flat backing behind."""
    from mathutils import noise as mnoise
    ys = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    y0, y1, z0, z1 = min(ys), max(ys), min(zs), max(zs)
    lifts = []
    z = z0
    while z < z1:
        lifts.append(z)
        z += rng.uniform(0.09, 0.14)

    def xoff(y, z):
        k = 0
        for j, zl in enumerate(lifts):
            if z >= zl + 0.010 * mnoise.noise(Vector((y * 5.0, zl * 3.0, 0.5))):
                k = j
        lump = 0.0060 * mnoise.noise(Vector((y * 18.0, z * 22.0, 1.3))) + 0.0025 * mnoise.noise(Vector((y * 70.0, z * 70.0, 7.1)))
        return 0.004 + (0.005 if k % 2 else 0.0) + lump

    n = len(poly)
    edges = []
    for i in range(n):
        (ay, az), (by, bz) = poly[i], poly[(i + 1) % n]
        # inside (CCW polygon): (b - a) x (p - a) >= 0  ->  -(bz - az) * y + (by - ay) * z >= -(bz - az) * ay + (by - ay) * az
        # as a <= c half plane for convex_clip: (bz - az) * y - (by - ay) * z <= (bz - az) * ay - (by - ay) * az
        edges.append((bz - az, -(by - ay), (bz - az) * ay - (by - ay) * az))
    verts, faces = [], []
    ny, nz = int((y1 - y0) / step) + 1, int((z1 - z0) / step) + 1
    for i in range(ny):
        for j in range(nz):
            ya, za = y0 + i * step, z0 + j * step
            cell = [(ya, za), (ya + step, za), (ya + step, za + step), (ya, za + step)]
            for (a_, b_, c_) in edges:
                cell = G.convex_clip(cell, a_, b_, c_)
                if len(cell) < 3:
                    break
            if len(cell) < 3 or abs(G.poly_area(cell)) < 1e-7:
                continue
            base = len(verts)
            for (y, z) in cell:
                verts.append(Vector((x_cut + xoff(y, z), y, z)))
            for k in range(1, len(cell) - 1):
                faces.append((base, base + k, base + k + 1))
    ge = G.Geo()
    ge.add(verts, faces, "M_DK_SectionEarth", None, None, smooth=set(range(len(faces))), jit=False)
    g.extend(G.weld(ge, 1e-6))          # the cells share their corners: one smooth surface, not a mosaic
    for k in range(int((y1 - y0) * (z1 - z0) * 14)):          # pebbles in the earth
        y, z = rng.uniform(y0 + 0.03, y1 - 0.03), rng.uniform(z0 + 0.03, z1 - 0.03)
        if any(a_ * y + b_ * z > c_ - 0.02 for (a_, b_, c_) in edges):
            continue
        r = rng.uniform(0.012, 0.024)
        pts = [(y + r * math.cos(t_) * rng.uniform(0.75, 1.1), z + r * 0.8 * math.sin(t_) * rng.uniform(0.75, 1.1))
               for t_ in [2 * math.pi * q / 6 for q in range(6)]]
        G.hewn_stone(g, pts, (x_cut + xoff(y, z) - 0.006, 0.0, 0.0), (0, 1, 0), (1, 0, 0), 0.01, 0.009, 9000 + k,
                     LIB_GR, chamfer=0.003, pitch=0.002, tilt=0.05, step=0.02)
    G.prism(g, [Vector((x_cut - 0.004, y, z)) for (y, z) in poly], (1, 0, 0), 0.02, "M_DK_SectionEarth")


def section_copy(objs, x_cut):
    """Copies of the module meshes cut at x = x_cut (keeps x < x_cut), plus the modelled section fills."""
    import bmesh
    earth = section_earth()
    mats = {n: bpy.data.materials[n] for n in (LIB_EP, LIB_RB, LIB_GR, LIB_TA, LIB_TE) if n in bpy.data.materials}
    mats["M_DK_SectionEarth"] = earth
    out = []
    fills = []            # (kind, [(y, z)], (y0, y1, z0, z1))
    for o in objs:
        me = o.data.copy()
        me.name = o.data.name + "_section"
        names = [m.name for m in me.materials]
        if LIB_TE not in names and LIB_TE in mats:
            me.materials.append(mats[LIB_TE])
            names.append(LIB_TE)
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.transform(o.matrix_world)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-6,
                               plane_co=(x_cut, 0, 0), plane_no=(1, 0, 0), clear_outer=True, clear_inner=False)
        edges = [e for e in bm.edges if len(e.link_faces) == 1 and all(abs(v.co.x - x_cut) < 1e-4 for v in e.verts)]
        new_faces = bmesh.ops.holes_fill(bm, edges=edges, sides=0)["faces"] if edges else []
        uvl = bm.loops.layers.uv.get("UV0") or bm.loops.layers.uv.verify()
        drop = []
        for f in new_faces:
            nb = [lf for e in f.edges for lf in e.link_faces if lf is not f]
            src = names[nb[0].material_index] if nb else ""
            poly = [(v.co.y, v.co.z) for v in f.verts]
            ys, zs = [p[0] for p in poly], [p[1] for p in poly]
            bbox = (min(ys), max(ys), min(zs), max(zs))
            if src == LIB_RB and (bbox[1] - bbox[0]) > 0.5:          # the footing's core: packed rubble (below)
                fills.append(("rubble", poly, bbox))
                drop.append(f)
                continue
            if src == LIB_EP and bbox[2] < 1.4:                        # plaster body: modelled below
                fills.append(("body", poly, bbox))
                drop.append(f)
                continue
            if src in (LIB_EP, "M_DJ_RoofTile") and bbox[2] >= 1.4 and (bbox[1] - bbox[0]) > 0.3:   # the cap's bed
                fills.append(("bed", poly, bbox))
                drop.append(f)
                continue
            if src == LIB_RB:            # a cut field stone shows granite inside, not the rubble pattern
                if LIB_GR not in names:
                    me.materials.append(mats[LIB_GR])
                    names.append(LIB_GR)
                f.material_index = names.index(LIB_GR)
            else:
                f.material_index = names.index(LIB_TE) if src == LIB_TA else (nb[0].material_index if nb else 0)
            rr = random.Random(len(fills) * 17 + len(drop))
            ou, ov = rr.random(), rr.random()
            for loop in f.loops:
                loop[uvl].uv = (loop.vert.co.y / (2.0 if src == LIB_TA else 4.0) + ou,
                                loop.vert.co.z / (2.0 if src == LIB_TA else 4.0) + ov)
        if drop:
            bmesh.ops.delete(bm, geom=drop, context="FACES_ONLY")
        bm.transform(o.matrix_world.inverted())
        bm.to_mesh(me)
        bm.free()
        c = bpy.data.objects.new(o.name + "_cut", me)
        c.matrix_world = o.matrix_world
        coll("Sheet").objects.link(c)
        o.hide_render = True
        out.append(c)
    # the modelled fills, in world space on the plane x = x_cut (t = -y .. no: t = +y along, n = +x out, up = z)
    t, n = Vector((0, 1, 0)), Vector((1, 0, 0))
    rng = random.Random(11)
    g = G.Geo()
    for kind, poly, (y0, y1, z0, z1) in fills:
        origin = (x_cut, 0.0, 0.0)
        cpoly = [(y, z) for (y, z) in poly]
        if G.poly_area(cpoly) < 0:
            cpoly = list(reversed(cpoly))
        if kind == "rubble":
            # the packed core: small hewn field stones (12-18 cm, granite) set 1-1.5 cm proud of a dark rubble
            # backing 3 cm back (deep joints, the gaps packed with spalls)
            G.prism(g, [Vector((x_cut - 0.03, y, z)) for (y, z) in cpoly], (1, 0, 0), 0.02, LIB_RB)
            seeds = []
            zz = z0 + 0.06
            row = 0
            while zz < z1:
                yy = y0 + (0.07 if row % 2 else 0.0) + rng.uniform(-0.03, 0.03)
                while yy < y1 + 0.1:
                    seeds.append((yy + rng.uniform(-0.03, 0.03), zz + rng.uniform(-0.025, 0.025)))
                    yy += rng.uniform(0.12, 0.19)
                zz += rng.uniform(0.11, 0.15)
                row += 1
            for i, cell in enumerate(G.voronoi_cells(seeds, y0, y1, z0, z1)):
                inner = G.inset_convex(G.clean_poly(cell), rng.uniform(0.006, 0.011))
                if inner is None or abs(G.poly_area(inner)) < 0.002:
                    continue
                G.hewn_stone(g, inner, origin, t, n, 0.035, rng.uniform(0.004, 0.012), 5000 + i, LIB_GR,
                             chamfer=0.010, pitch=0.005, tilt=0.03, step=0.04)
            continue
        # plaster skin (25 mm, the body only) round a rammed-earth core in lifts
        inner = G.inset_convex(G.clean_poly(cpoly), 0.025) if kind == "body" else G.clean_poly(cpoly)
        if kind == "body":
            G.prism(g, [Vector((x_cut, y, z)) for (y, z) in cpoly], (1, 0, 0), 0.02, LIB_EP)
        if inner is None:
            continue
        earth_face(g, inner, x_cut, rng)
    out.append(geo_to_object(g, "SectionFill", x_cut, mats))
    return out


def section_plinth(x0, x1, y0, y1):
    """The buried foundation slab under the footing (shown in the section only, as on the sheet)."""
    me = bpy.data.meshes.new("SectionSlab")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.transform(Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, -0.07)) @ Matrix.Diagonal((x1 - x0, y1 - y0, 0.14, 1)))
    uvl = bm.loops.layers.uv.new("UV0")
    for f in bm.faces:
        for loop in f.loops:
            co = loop.vert.co
            loop[uvl].uv = ((co.x + co.y) / 4.0, co.z / 4.0 if abs(f.normal.z) < 0.5 else co.y / 4.0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(bpy.data.materials[LIB_GR])
    o = bpy.data.objects.new("SectionSlab", me)
    coll("Sheet").objects.link(o)
    return o


def render_wall():
    sheet_look()
    hide_assembly(True)
    S = coll("Sheet")
    # straight run: End (turned) + 2 m + End, at x 100..104, inner face y = 0
    ox = 100.0
    wall_module(1, ox, 0.0, 0.0, kind="end", flip=True)
    wall_module(2, ox + 1, 0.0, 0.0)
    wall_module(1, ox + 3, 0.0, 0.0, kind="end")
    shadow_catcher(ox + 2, -0.5)
    zc = 1.05
    # front elevation (outer face, camera at -y looking +y): the silhouette stands left of the run
    ortho_view("wall_front", (ox + 1.55, -0.5, 1.25), "+y", 6.2, 1100, 520, {"model_x": [ox - 0.17, ox + 4.17]})
    # side elevation (the gable end, camera at +x looking -x): silhouette at +y side
    ortho_view("wall_side", (ox + 2, -0.1, 1.25), "-x", 2.6, 460, 520)
    # top view
    ortho_view("wall_top", (ox + 2, -0.5, 1.0), "-z", 5.2, 920, 300)
    # the gabled end in 3/4 (tie beam, bargeboards, the footing wrapping the end)
    cam = persp_cam("CAM_wall_end34", (ox + 6.4, -3.4, 2.2), (ox + 3.6, -0.5, 1.05), lens=45)
    render(cam, "wall_end_34", 700, 700)
    # 3/4 perspective from outside-left, a little above eye height
    cam = persp_cam("CAM_wall34", (ox - 3.6, -6.2, 2.6), (ox + 1.9, -0.4, 0.95), lens=40)
    render(cam, "wall_34", 1000, 640)
    # section cut: a copy of the run cut at x = ox + 2 (the middle of the 2 m module), seen from the cut side, on the
    # buried foundation slab (the sheet's section view)
    objs = [o for o in S.objects if o.get("sheet")]
    cut = section_copy(objs, ox + 2.0)
    slab = section_plinth(ox + 0.2, ox + 2.12, -1.14, 0.14)
    cam = persp_cam("CAM_section", (ox + 5.4, -1.55, 1.75), (ox + 1.9, -0.5, 1.05), lens=46)
    # r2: a raking light across the cut (the sheet key lights the faces the other views show, so the cut read flat)
    rk = bpy.data.lights.new("SectionRake", "AREA")
    rk.energy = 260.0
    rk.size = 1.2
    rko = bpy.data.objects.new("SectionRake", rk)
    coll("Sheet").objects.link(rko)
    rko.location = (ox + 3.2, 1.6, 2.9)
    rko.rotation_euler = (Vector((ox + 2.0, -0.5, 1.0)) - rko.location).to_track_quat("-Z", "Y").to_euler()
    render(cam, "wall_section", 640, 800)
    bpy.data.objects.remove(rko, do_unlink=True)
    for c in cut + [slab]:
        bpy.data.objects.remove(c, do_unlink=True)
    for o in objs:
        o.hide_render = False
    # outside corner at (200, 0): corner block + 1 m + End on both legs
    cx = 200.0
    inst("SM_DK_WallFooting_Corner", (cx, 0, 0), 0.0)
    inst("SM_DK_WallBody_1m_T200", (cx - 1, 0, FH), 0.0)
    inst("SM_DK_WallCap_Corner", (cx, 0, ZB["T200"]), 0.0)
    wall_module(1, cx, 0.0, 0.0)
    wall_module(1, cx + 1, 0.0, 0.0, kind="end")
    # y-leg (x in [cx-1, cx]) running +y: the east-side frame (rot 90, pivot x = cx - 1)
    for a, kind in ((0.0, "straight"), (1.0, "end")):
        R = Matrix.Rotation(math.radians(90.0), 4, "Z")
        parts = ((("SM_DK_WallFooting_1m" if kind == "straight" else "SM_DK_WallFooting_End"), 0.0),
                 ("SM_DK_WallBody_1m_T200", FH),
                 (("SM_DK_WallCap_1m" if kind == "straight" else "SM_DK_WallCap_End"), ZB["T200"]))
        for p, z in parts:
            inst(p, (cx - 1.0, a, z), 90.0)
        _ = R
    shadow_catcher(cx, 0)
    cam = persp_cam("CAM_corner_out", (cx - 5.6, -5.2, 2.9), (cx + 0.1, 0.2, 0.9), lens=40)
    render(cam, "corner_34_out", 900, 640)
    cam = persp_cam("CAM_corner_in", (cx + 4.4, 3.9, 3.1), (cx - 0.4, -0.3, 1.0), lens=40)
    render(cam, "corner_34_in", 900, 640)
    ortho_view("corner_top", (cx + 0.1, 0.1, 1.0), "-z", 3.6, 560, 560)
    # corner elevation seen diagonally from outside (the sheet's corner view)
    d = Vector((1, 1, 0)).normalized()
    camo = ortho_cam("CAM_corner_elev", (cx - 0.3, -0.3, 1.05), d, (0, 0, 1), 4.6, 700, 440)
    camo.matrix_world = Matrix.Translation(Vector((cx - 0.3, -0.3, 1.05)) - d * 60) @ d.to_track_quat("-Z", "Y").to_matrix().to_4x4()
    render(camo, "corner_elev", 700, 440)
    VIEWS["corner_elev"] = {"ppm": 700 * SCALE / 4.6, "w": int(700 * SCALE), "h": int(440 * SCALE),
                            "centre": [cx - 0.3, -0.3, 1.05], "forward": "diag"}
    # f1: the freestanding timber-framed pier (the wall sheet's bottom-right piece), near-front on its gabled end
    fx = 150.0
    inst("SM_DK_Wall_FramePier", (fx, 0, 0), 0.0)
    shadow_catcher(fx + 0.5, -0.5, 20.0)
    cam = persp_cam("CAM_framepier", (fx + 4.6, -2.2, 1.55), (fx + 0.5, -0.5, 1.02), lens=55)
    render(cam, "frame_pier", 600, 800)


def render_variants():
    sheet_look()
    hide_assembly(True)
    ox = 400.0
    for i, key in enumerate(("T200", "T250", "T300")):
        x0 = ox + i * 5.0
        wall_module(1, x0, 0.0, 0.0, key=key, kind="end", flip=True)
        wall_module(2, x0 + 1, 0.0, 0.0, key=key)
        wall_module(1, x0 + 3, 0.0, 0.0, key=key, kind="end")
    shadow_catcher(ox + 7, -0.5, 60)
    ortho_view("wall_variants", (ox + 6.6, -0.5, 1.55), "+y", 16.0, 1600, 520)


# ------------------------------------------------------------------------------------------------ GATE sheet
GATE_X = 22.0
LEAVES = K["gate_leaf_placements"]
LAMP_LIGHTS = K["lamp_lights_world"]
LAMP_PLACES = [(i["loc"], i["rot_z"]) for i in L["instances"] if i["piece"] == "SM_DK_Gate_Lamp"]


def gate_assembly(ox, open_leaves=False):
    g = Vector((ox, 0.0, 0.0))
    for p in ("SM_DK_Gate_Frame", "SM_DK_Gate_Roof", "SM_DK_Gate_Paving"):
        inst(p, g, 0.0)
    set_leaves(ox, open_leaves)
    for loc, rot in LAMP_PLACES:
        inst("SM_DK_Gate_Lamp", Vector(loc) + Vector((ox - GATE_X, 0, 0)), rot)
    # f2: the wall runs straight into the gate's post clusters (the 0.5 m join pieces under the verge). r2: no
    # route-6 stands (removed: nothing stands outside the gate roof)
    inst("SM_DK_Wall_GateJoin", g + Vector((-4.0, 0.0, 0.0)), 0.0)
    inst("SM_DK_Wall_GateJoin", g + Vector((4.0, -1.0, 0.0)), 180.0)
    # wall each side: End (turned) + 2 m on the left, 2 m + End on the right
    wall_module(1, ox - 7.0, 0.0, 0.0, kind="end", flip=True)
    wall_module(2, ox - 6.0, 0.0, 0.0)
    wall_module(2, ox + 4.0, 0.0, 0.0)
    wall_module(1, ox + 6.0, 0.0, 0.0, kind="end")


def set_leaves(ox, open_leaves):
    for o in list(coll("Sheet").objects):
        if o.name.startswith("SM_DK_Gate_Leaf"):
            bpy.data.objects.remove(o, do_unlink=True)
    for it in LEAVES["open" if open_leaves else "closed"]:
        inst(it["piece"], Vector(it["loc"]) + Vector((ox - GATE_X, 0, 0)), it["rot_z"])


def lamp_lights(ox, c=None, energy=40.0):
    for p in LAMP_LIGHTS:
        lt = bpy.data.lights.new("LampLight", "POINT")
        lt.energy = energy
        lt.color = (1.0, 0.60, 0.28)
        lt.shadow_soft_size = 0.08
        o = bpy.data.objects.new("LampLight", lt)
        (c or coll("Sheet")).objects.link(o)
        o.location = Vector(p) + Vector((ox - GATE_X, 0, 0))


def render_gate():
    sheet_look()
    hide_assembly(True)
    ox = 300.0
    gate_assembly(ox)
    lamp_lights(ox)
    shadow_catcher(ox, 0)
    ortho_view("gate_front", (ox, 0.0, 2.45), "+y", 14.4, 1180, 560)
    # side elevation with the wall passing through (the sheet's side view): on the camera side the wall is cut short
    # to its gabled End just outside the verge (the join + a 1 m End), so the wall's end reads in front of the post
    # cluster as on the sheet; gate_side hides the route-6 stand, gate_side_stand shows it
    east = [o for o in coll("Sheet").objects if o.get("sheet") and o.matrix_world.translation.x > ox + 4.05
            and not o.name.startswith(("SM_DK_Gate_Lamp", "SM_DK_Gate_Leaf", "Catcher"))]
    for o in east:
        o.hide_render = True
    tmp = wall_module(1, ox + 4.0, 0.0, 0.0, kind="end")
    ortho_view("gate_side", (ox, 0.1, 2.45), "-x", 7.2, 560, 560)
    for o in tmp:
        bpy.data.objects.remove(o, do_unlink=True)
    for o in east:
        o.hide_render = False
    cam = persp_cam("CAM_gate34", (ox - 9.5, -11.0, 3.3), (ox - 0.2, -0.3, 2.0), lens=38)
    render(cam, "gate_34", 1000, 700)
    # a closer look at the doors from the street (hardware), eye height
    cam = persp_cam("CAM_gate_doors", (ox + 1.4, -6.2, 1.7), (ox - 0.2, -0.7, 1.75), lens=40)
    render(cam, "gate_doors_close", 900, 640)
    # f2 top views with the doors open and the roof ON (the judge: the f1 plan was cut at +3.0 and showed no roof):
    # the true plan, and the reference's oblique top view (ortho from above the street at 38 deg, the open leaves
    # showing under the eave, as on the sheet)
    set_leaves(ox, True)
    ortho_view("gate_top", (ox, 0.0, 2.0), "-z", 14.4, 1000, 460)
    d = Vector((0.0, math.cos(math.radians(38.0)), -math.sin(math.radians(38.0))))
    camo = ortho_cam("CAM_gate_top_oblique", (ox, 0.0, 1.6), d, (0, 0, 1), 14.4, 1000, 640)
    for c_ in CATCHERS:
        c_.hide_render = True
    render(camo, "gate_top_oblique", 1000, 640)
    for c_ in CATCHERS:
        c_.hide_render = False
    # doors-open view from outside at eye height (shows the leaves swung in, the 4.0 m passage)
    cam = persp_cam("CAM_gate_open", (ox + 0.0, -9.0, 1.6), (ox, 0.0, 1.9), lens=35)
    render(cam, "gate_open_front", 900, 640)
    # courtyard side 3/4 (the side the 1v1 players see)
    set_leaves(ox, False)
    cam = persp_cam("CAM_gate34_in", (ox + 8.5, 10.0, 3.0), (ox + 0.2, 0.3, 2.1), lens=38)
    render(cam, "gate_34_courtyard", 1000, 700)


# ------------------------------------------------------------------------------------------------ BEAUTY
def sunset_world():
    """A painted sunset sky: warm glow toward the sun near the horizon, violet-blue overhead (reference 2)."""
    world = bpy.data.worlds.new("Sunset")
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    s = L["sun"]
    el, az = math.radians(s["elev_deg"]), math.radians(s["azimuth_deg_from_x"])
    to_sun = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    nt.links.new(tc.outputs["Generated"], dot.inputs[0])
    dot.inputs[1].default_value = to_sun
    # vertical gradient
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (1.0, 0.52, 0.26, 1)
    cr.elements[1].position = 0.35
    cr.elements[1].color = (0.30, 0.28, 0.46, 1)
    e = cr.elements.new(0.08)
    e.color = (0.95, 0.55, 0.42, 1)
    nt.links.new(sep.outputs[2], ramp.inputs["Fac"])
    # sun glow
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    mx.inputs[1].default_value = 0.0
    nt.links.new(dot.outputs["Value"], mx.inputs[0])
    nt.links.new(mx.outputs[0], pw.inputs[0])
    pw.inputs[1].default_value = 6.0
    glow = nt.nodes.new("ShaderNodeMix")
    glow.data_type = "RGBA"
    glow.blend_type = "ADD"
    nt.links.new(pw.outputs[0], glow.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], glow.inputs["A"])
    glow.inputs["B"].default_value = (1.0, 0.62, 0.30, 1)
    # below the horizon: dark ground colour
    below = nt.nodes.new("ShaderNodeMath")
    below.operation = "LESS_THAN"
    below.inputs[1].default_value = 0.0
    nt.links.new(sep.outputs[2], below.inputs[0])
    gmix = nt.nodes.new("ShaderNodeMix")
    gmix.data_type = "RGBA"
    nt.links.new(below.outputs[0], gmix.inputs["Factor"])
    nt.links.new(glow.outputs["Result"], gmix.inputs["A"])
    gmix.inputs["B"].default_value = (0.12, 0.10, 0.09, 1)
    nt.links.new(gmix.outputs["Result"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    sc.world = world
    lt = bpy.data.lights.new("Sun", "SUN")
    lt.energy = 4.2
    lt.angle = math.radians(0.8)
    lt.color = (1.0, 0.63, 0.36)
    so = bpy.data.objects.new("Sun", lt)
    sc.collection.objects.link(so)
    so.rotation_euler = (-to_sun).to_track_quat("-Z", "Y").to_euler()


GROUND_BLEND = ROOT / "Assets" / "Dojo" / "DojoGround.blend"
GREY_FLOORS = ("SM_DGB_Floor_Fight", "SM_DGB_Floor_Path", "SM_DGB_Floor_Yards")


def add_ground_kit():
    """r2 context: the kit-2 ground (DojoGround.blend's Assembly, appended read-only) in place of the grey-box floors;
    ground pieces under the gate paving (X 18.1-25.9, Y -3.0..2.0) are left out, as the showcase does."""
    if not GROUND_BLEND.exists():
        return 0
    with bpy.data.libraries.load(str(GROUND_BLEND), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if "__" in n and not n.startswith("UCX_")]
    c = coll("Ground")
    k = 0
    for o in dst.objects:
        if o is None:
            continue
        pts = [o.matrix_world @ Vector(b) for b in o.bound_box]
        cx = sum(q.x for q in pts) / 8
        cy = sum(q.y for q in pts) / 8
        if 18.1 <= cx <= 25.9 and -3.0 <= cy <= 2.0:
            continue
        c.objects.link(o)
        k += 1
    for o in bpy.data.collections["Assembly"].objects:
        if o.name.startswith(GREY_FLOORS):
            o.hide_render = True
    return k


def render_beauty():
    setup_cycles()
    sc.render.film_transparent = False
    sunset_world()
    hide_assembly(False)
    print("ground pieces added:", add_ground_kit())
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    sc.view_settings.exposure = 0.6
    lamp_lights(GATE_X, coll("Lights"), energy=45.0)
    cam = persp_cam("CAM_gate_from_court", (22.0, 13.5, 1.65), (22.0, -0.6, 2.35), lens=30)
    render(cam, "beauty_gate_from_courtyard", 1600, 1000)
    # along the east wall's inner face (it faces the low west sun): the residence pier and roof at the far end
    cam = persp_cam("CAM_along_wall", (42.3, 6.2, 1.65), (44.3, 28.0, 2.0), lens=26)
    render(cam, "beauty_along_east_wall", 1600, 1000)
    # reference-2 framing: through the OPEN gate (the BR state), from just outside the threshold, eye height
    for it in LEAVES["open"]:
        for o in bpy.data.collections["Assembly"].objects:
            if o.name.startswith(it["piece"] + "__"):
                o.matrix_world = Matrix.Translation(it["loc"]) @ Matrix.Rotation(math.radians(it["rot_z"]), 4, "Z")
    cam = persp_cam("CAM_ref2", (22.0, -2.6, 1.75), (22.0, 30.0, 0.9), lens=18.0 / math.tan(math.radians(74.0) / 2))
    render(cam, "beauty_ref2_through_open_gate", 1448, 1086)


def render_closeups():
    """r2 key close-ups (studio grey, like the sheets): the footing at eye height, the wall end, the section, the gate's
    wall junction and plinths, the verge and ridge end."""
    sheet_look()
    hide_assembly(True)
    ox = 600.0
    wall_module(1, ox, 0.0, 0.0, kind="end", flip=True)
    wall_module(4, ox + 1, 0.0, 0.0)
    wall_module(1, ox + 5, 0.0, 0.0, kind="end")
    shadow_catcher(ox + 3, -0.5)
    cam = persp_cam("CAM_foot_close", (ox + 2.2, -2.3, 0.75), (ox + 2.9, -1.0, 0.36), lens=50)
    render(cam, "close_footing", 1200, 800)
    cam = persp_cam("CAM_end_close", (ox + 7.6, -1.9, 1.2), (ox + 6.0, -0.5, 0.9), lens=40)
    render(cam, "close_wall_end", 900, 1000)
    gx = 700.0
    gate_assembly(gx)
    lamp_lights(gx)
    wall_module(2, gx - 6.0, 0.0, 0.0)
    wall_module(2, gx + 4.0, 0.0, 0.0)
    shadow_catcher(gx, 0)
    cam = persp_cam("CAM_gate_junction", (gx - 6.2, -3.2, 1.6), (gx - 3.6, -0.6, 1.3), lens=35)
    render(cam, "close_gate_junction", 1100, 800)
    cam = persp_cam("CAM_gate_ridge_end", (gx - 6.6, -3.6, 5.3), (gx - 4.0, 0.0, 4.4), lens=45)
    render(cam, "close_gate_ridge_end", 1100, 800)
    cam = persp_cam("CAM_gate_court_corner", (gx - 6.5, 4.8, 1.7), (gx - 3.6, 1.2, 1.9), lens=30)
    render(cam, "close_gate_courtyard_corner", 1100, 800)


if WHAT == "wall":
    render_wall()
elif WHAT == "closeups":
    render_closeups()
elif WHAT == "variants":
    render_variants()
elif WHAT == "gate":
    render_gate()
elif WHAT == "beauty":
    render_beauty()
vp = OUT / "views.json"
old = json.loads(vp.read_text(encoding="utf-8")) if vp.exists() else {}
old.update(VIEWS)
vp.write_text(json.dumps(old, indent=1), encoding="utf-8")
