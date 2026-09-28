"""b2_rig_mesh.py - PRIVATE / DO NOT SHIP. Step C1 stage 1: the game meshes, still in the step A (posed) space.

  blender -b WorkFiles/Characters/2B_private/2B_private_base.blend -P Scripts/Characters/b2_rig_mesh.py

Reads the step A base blend (never saved over) and writes rig_work/c1_stage1_mesh.blend with:
  SK_2B_Body       exact L1 un-subdivided welded skin shell (TEST_SkinShell_exact1), source UVs, 11 surface materials
  SK_2B_HeadParts  eyes (EyeMoisture/Tear decimated), teeth decimated to <= 6k tris, UPPER eyelash cards only
  SK_2B_Garments   CLO_Underwear + CLO_BasicTop (bandeau made from the chest faces of the skin shell, +2 mm)
plus the Render_Rig collection (render only, never exported).
"""
import bpy, bmesh, os, sys, math
from collections import defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_rig_common import *  # noqa

TOP_OFFSET = 0.002
DECIMATE = {"EyeMoisture": 0.3, "Tear": 0.3}
TEETH_MAX_TRIS = 6000


def mat_rename(m, short):
    m.name = "M_2B_" + short
    return m


def clean_normals(me):
    for a in list(me.attributes):
        if a.name in ("custom_normal", "sharp_face"):
            me.attributes.remove(a)

    for p in me.polygons:
        p.use_smooth = True


def components(bm):
    seen = set(); comps = []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack = [f]; comp = []; seen.add(f.index)
        while stack:
            g = stack.pop(); comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index); stack.append(h)
        comps.append(comp)
    return comps


def copy_obj(name, new_name):
    src = bpy.data.objects[name]
    o = bpy.data.objects.new(new_name, src.data.copy())
    o.data.name = new_name
    return o


def decimate(o, ratio):
    m = o.modifiers.new("dec", 'DECIMATE'); m.decimate_type = 'COLLAPSE'; m.ratio = ratio
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    o.modifiers.remove(m)
    old = o.data; o.data = me; me.name = old.name
    bpy.data.meshes.remove(old)


def build_top(skin):
    """Simple fitted bandeau from the skin shell's chest faces (src == Body)."""
    me = skin.data
    src = me.attributes["src"].data
    body_i = SHELL.index("Body")
    cand = [v.co for v in me.vertices if 1.12 < v.co.z < 1.45 and abs(v.co.x) < 0.16]
    apex = min(cand, key=lambda c: c.y)
    z0, z1 = apex.z - 0.085, apex.z + 0.065
    apex_cx = sum(v.co.x for v in me.vertices if abs(v.co.z - apex.z) < 0.01 and abs(v.co.x) < 0.2) / max(1, sum(
        1 for v in me.vertices if abs(v.co.z - apex.z) < 0.01 and abs(v.co.x) < 0.2))
    bm = bmesh.new(); bm.from_mesh(me)
    sl = bm.faces.layers.int.get("src")
    keep = set()
    for f in bm.faces:
        c = f.calc_center_median()
        # the upper edge drops 2.5 cm towards the sides so the band stays below the armpits
        side = min(1.0, max(0.0, (abs(c.x - apex_cx) - 0.05) / 0.07))
        ztop = z1 - 0.025 * side * side * (3 - 2 * side)
        if f[sl] == body_i and z0 < c.z < ztop:
            keep.add(f)
    # also take Arms faces of the front/back armpit strip that the Body surface leaves out (none expected)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in keep], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    # drop small islands (keep the band ring)
    comps = components(bm)
    comps.sort(key=len, reverse=True)
    for c in comps[1:]:
        bmesh.ops.delete(bm, geom=c, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.verts.ensure_lookup_table()
    # source vertex index (for exact weight copy later): nearest skin vertex = identical position
    kd_src = {tuple(round(x, 7) for x in v.co): v.index for v in me.vertices}
    srcidx = bm.verts.layers.int.new("skin_vert")
    miss = 0
    for v in bm.verts:
        k = tuple(round(x, 7) for x in v.co)
        if k in kd_src:
            v[srcidx] = kd_src[k]
        else:
            v[srcidx] = -1; miss += 1
    # smooth the two boundary loops in z (the face-centroid cut leaves a small staircase)
    for it in range(12):
        new = {}
        for v in bm.verts:
            if not v.is_boundary:
                continue
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2:
                new[v] = (v.co.z * 2 + nb[0].co.z + nb[1].co.z) / 4
        for v, z in new.items():
            v.co.z = z
    bm.normal_update()
    # bridge the cleavage and the spine groove: push verts out to the convex hull of their horizontal slice
    import mathutils.geometry as mg
    bins = defaultdict(list)
    for v in bm.verts:
        bins[int(v.co.z / 0.006)].append(v)
    moved = 0
    for k, vs in bins.items():
        pts = [v.co.xy for v in vs]
        if len(pts) < 8:
            continue
        hull = mg.convex_hull_2d(pts)
        poly = [pts[i] for i in hull]
        cen = sum(poly, Vector((0, 0))) / len(poly)
        for v in vs:
            p = v.co.xy
            if v.co.y > 0.02 and abs(v.co.x) > 0.04:
                continue  # sides/back: only the spine groove (|x| small) is bridged at the back
            best = None
            for i in range(len(poly)):
                a = poly[i]; b = poly[(i + 1) % len(poly)]
                ab = b - a
                t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
                q = a + ab * t
                d = (q - p).length
                if best is None or d < best[0]:
                    best = (d, q)
            if best and best[0] > 0.0005:
                # only move outward (hull points are outside or on the slice)
                if (best[1] - cen).length > (p - cen).length:
                    v.co.x, v.co.y = best[1].x, best[1].y
                    moved += 1
    bm.normal_update()
    # relax the whole band (Laplacian; boundary verts only along their boundary loop, in 3D) so the hull bridge and
    # the face-centroid cut do not leave facets / a sawtooth edge, then keep it on or outside the skin
    skin_tree = BVHTree.FromPolygons([v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    for it in range(10):
        new = {}
        for v in bm.verts:
            if v.is_boundary:
                nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
                if len(nb) == 2:
                    new[v] = v.co * 0.5 + (nb[0].co + nb[1].co) * 0.25
            else:
                nb = [e.other_vert(v) for e in v.link_edges]
                new[v] = v.co * 0.5 + sum((w.co for w in nb), Vector()) / len(nb) * 0.5
        for v, c in new.items():
            v.co = c
        for v in bm.verts:
            loc, nrm, fi, d = skin_tree.find_nearest(v.co)
            if loc is not None and (v.co - loc).dot(nrm) < 0:
                v.co = loc.copy()
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * TOP_OFFSET
    for v in bm.verts:  # guarantee the gap after the normal offset
        loc, nrm, fi, d = skin_tree.find_nearest(v.co)
        if loc is not None and (v.co - loc).dot(nrm) < TOP_OFFSET * 0.9:
            v.co = loc + nrm * TOP_OFFSET
    # rolled inner lip on both edges (2 mm inward) so the edge is not paper-thin
    bm.normal_update()
    bedges = [e for e in bm.edges if e.is_boundary]
    ret = bmesh.ops.extrude_edge_only(bm, edges=bedges)
    newv = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in newv:
        # the new vert sits where its source is; push it back towards the skin
        n = Vector()
        for e in v.link_edges:
            w = e.other_vert(v)
            for f in w.link_faces:
                n += f.normal
        if n.length > 0:
            v.co -= n.normalized() * (TOP_OFFSET * 0.9)
        v[srcidx] = v[srcidx]
    bm.normal_update()
    tme = bpy.data.meshes.new("CLO_BasicTop")
    bm.to_mesh(tme); bm.free()
    for a in list(tme.attributes):
        if a.name in ("src", "sharp_face"):
            tme.attributes.remove(a)
    for p in tme.polygons:
        p.use_smooth = True
    log("top z-range", round(z0, 3), round(z1, 3), "moved to hull", moved, "missing src verts", miss)
    o = bpy.data.objects.new("CLO_BasicTop", tme)
    mat = bpy.data.materials.new("M_2B_BasicTop")
    b = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (0.075, 0.075, 0.08, 1); b.inputs["Roughness"].default_value = 0.85
    tme.materials.append(mat)
    return o, (z0, z1)


def main():
    assert bpy.data.filepath.replace("\\", "/").endswith("2B_private_base.blend"), bpy.data.filepath
    os.makedirs(WORK, exist_ok=True)
    info = {}
    coll = bpy.data.collections.new("C1_Game"); bpy.context.scene.collection.children.link(coll)

    # ---------------- skin
    skin = copy_obj("TEST_SkinShell_exact1", "SK_2B_Body")
    me = skin.data
    me.materials.clear()
    for s in SHELL:
        me.materials.append(mat_rename(bpy.data.materials[s], s))
    src = [0] * len(me.polygons)
    me.attributes["src"].data.foreach_get("value", src)
    me.polygons.foreach_set("material_index", src)
    clean_normals(me)
    coll.objects.link(skin)
    info["skin"] = {"verts": len(me.vertices), "faces": len(me.polygons), "tris": tris_of(me)}

    # ---------------- head parts
    parts = []
    for s in EYE_PARTS:
        o = copy_obj("BODY_" + s, "HP_" + s)
        coll.objects.link(o)
        if s in DECIMATE:
            decimate(o, DECIMATE[s])
        o.data.materials.clear(); o.data.materials.append(mat_rename(bpy.data.materials[s], s))
        clean_normals(o.data)
        parts.append(o)
    teeth = copy_obj("BODY_Teeth", "HP_Teeth"); coll.objects.link(teeth)
    t0 = tris_of(teeth.data)
    decimate(teeth, (TEETH_MAX_TRIS * 0.97) / t0)
    teeth.data.materials.clear(); teeth.data.materials.append(mat_rename(bpy.data.materials["Teeth"], "Teeth"))
    clean_normals(teeth.data)
    parts.append(teeth)
    info["teeth_tris"] = [t0, tris_of(teeth.data)]
    # lashes: keep upper cards only
    lash = copy_obj("BODY_Eyelashes", "HP_Lashes"); coll.objects.link(lash)
    ir = bpy.data.objects["BODY_Irises"].data.vertices
    eye_z = sum(v.co.z for v in ir) / len(ir)
    bm = bmesh.new(); bm.from_mesh(lash.data)
    comps = components(bm)
    rows = []; drop = []
    for c in comps:
        vs = {v for f in c for v in f.verts}
        cz = sum(v.co.z for v in vs) / len(vs)
        cy = sum(v.co.y for v in vs) / len(vs)
        cx = sum(v.co.x for v in vs) / len(vs)
        zmin = min(v.co.z for v in vs); zmax = max(v.co.z for v in vs)
        area = sum(f.calc_area() for f in c)
        rows.append({"faces": len(c), "centroid": [round(cx, 4), round(cy, 4), round(cz, 4)], "z": [round(zmin, 4), round(zmax, 4)],
                     "area_cm2": round(area * 1e4, 3)})
        uvl = bm.loops.layers.uv.active
        vmax = max(l[uvl].uv.y for f in c for l in f.loops)
        rows[-1]["uv_vmax"] = round(vmax, 3)
        if vmax < 0.13:  # lower-lash card strip of the lash texture (v 0.01-0.13); upper cards use v 0.13-0.26
            drop.extend(c)
    log("eye z", round(eye_z, 4)); [log("lash comp", r) for r in rows]
    bmesh.ops.delete(bm, geom=list(set(drop)), context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(lash.data); bm.free()
    lash.data.materials.clear(); lash.data.materials.append(mat_rename(bpy.data.materials["7_-mask.face_eyeslashes_0.15_0_0"], "Eyelashes"))
    clean_normals(lash.data)
    parts.append(lash)
    info["lash_components"] = rows; info["lash_eye_z"] = eye_z
    info["lash_faces_dropped"] = len(set(drop))
    # join head parts
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    per = {o.name: tris_of(o.data) for o in parts}
    bpy.ops.object.join()
    hp = bpy.context.view_layer.objects.active
    hp.name = "SK_2B_HeadParts"; hp.data.name = "SK_2B_HeadParts"
    info["headparts"] = {"per_part_tris": per, "tris": tris_of(hp.data)}

    # ---------------- garments
    uw = copy_obj("CLO_Underwear", "CLO_Underwear_game"); coll.objects.link(uw)
    uw.data.materials.clear(); uw.data.materials.append(mat_rename(bpy.data.materials["24_outfit_a_1.2_0_0_2B_Underware"], "Underwear"))
    for a in list(uw.data.attributes):
        if a.name in ("custom_normal",):
            uw.data.attributes.remove(a)
    # the skin under the gusset keeps the G8F anatomical detail, which peeks out of the leg openings: relax the skin
    # inside a small zone around the gusset (hidden by the briefs anyway) before the briefs are conformed to it
    uw_tree = BVHTree.FromPolygons([v.co for v in uw.data.vertices], [tuple(p.vertices) for p in uw.data.polygons])
    sme = skin.data
    zc = min(v.co.z for v in uw.data.vertices)
    zone = set()
    for v in sme.vertices:
        if v.co.z < zc + 0.06 and v.co.z > zc - 0.03 and abs(v.co.x) < 0.06:
            loc, nrm, fi, d = uw_tree.find_nearest(v.co)
            if loc is not None and d < 0.02:
                zone.add(v.index)
    nbrs = {i: [] for i in zone}
    for e in sme.edges:
        a, b = e.vertices
        if a in zone:
            nbrs[a].append(b)
        if b in zone:
            nbrs[b].append(a)
    border = {i for i in zone if any(n not in zone for n in nbrs[i])}
    for it in range(25):
        newc = {}
        for i in zone - border:
            c = sum((sme.vertices[n].co for n in nbrs[i]), Vector()) / len(nbrs[i])
            newc[i] = sme.vertices[i].co.lerp(c, 0.5)
        for i, c in newc.items():
            sme.vertices[i].co = c
    info["crotch_skin_relaxed_verts"] = len(zone - border)
    # the source briefs are coarse (944 tris) and float up to several mm off the skin: one flat subdivision, then
    # every vertex is conformed to 1.5 mm above the posed skin so the skin cannot poke through between vertices
    bm = bmesh.new(); bm.from_mesh(uw.data)
    nv0 = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)  # the GLB splits every edge; UVs stay per corner
    info["underwear_weld"] = [nv0, len(bm.verts)]
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    skin_tree = BVHTree.FromPolygons([v.co for v in skin.data.vertices], [tuple(p.vertices) for p in skin.data.polygons])
    conf = 0
    for v in bm.verts:
        loc, nrm, fi, d = skin_tree.find_nearest(v.co)
        if loc is not None and d < 0.012:
            v.co = loc + nrm * 0.0015
            conf += 1
    # relax (conforming onto the nearest skin point can pick the inner thigh at the gusset edge), keep the gap
    for it in range(4):
        newc = {}
        for v in bm.verts:
            nb = [e.other_vert(v) for e in v.link_edges]
            if v.is_boundary:
                nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if nb:
                newc[v] = v.co.lerp(sum((w.co for w in nb), Vector()) / len(nb), 0.5)
        for v, c in newc.items():
            v.co = c
        for v in bm.verts:
            loc, nrm, fi, d = skin_tree.find_nearest(v.co)
            if loc is not None and (v.co - loc).dot(nrm) < 0.0013:
                v.co = loc + nrm * 0.0015
    bm.to_mesh(uw.data); bm.free()
    info["underwear_conformed_verts"] = conf
    top, zr = build_top(skin); coll.objects.link(top)
    info["top"] = {"z_range": zr, "tris": tris_of(top.data), "verts": len(top.data.vertices)}
    info["underwear_tris"] = tris_of(uw.data)
    bpy.ops.object.select_all(action='DESELECT')
    uw.select_set(True); top.select_set(True)
    bpy.context.view_layer.objects.active = top
    bpy.ops.object.join()
    g = bpy.context.view_layer.objects.active
    g.name = "SK_2B_Garments"; g.data.name = "SK_2B_Garments"
    for p in g.data.polygons:
        p.use_smooth = True

    # ---------------- remove everything that is not game mesh or render rig
    keep = {"SK_2B_Body", "SK_2B_HeadParts", "SK_2B_Garments"} | {o.name for o in bpy.data.collections["Render_Rig"].objects}
    for o in list(bpy.data.objects):
        if o.name not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        if c.name not in ("C1_Game", "Render_Rig"):
            bpy.data.collections.remove(c)
    for _ in range(3):
        bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    tot = 0
    for n in ("SK_2B_Body", "SK_2B_HeadParts", "SK_2B_Garments"):
        o = bpy.data.objects[n]
        t = tris_of(o.data); tot += t
        info.setdefault("meshes", []).append({"name": n, "tris": t, "verts": len(o.data.vertices),
                                              "material_slots": len(o.data.materials),
                                              "materials": [m.name for m in o.data.materials]})
    info["total_tris"] = tot
    log(json.dumps(info, indent=1))
    save_json(WORK + "/c1_stage1_info.json", info)
    bpy.ops.wm.save_as_mainfile(filepath=STAGE1, compress=True)
    log("saved", STAGE1)


main()
