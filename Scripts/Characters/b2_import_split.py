"""b2_import_split.py - PRIVATE / DO NOT SHIP (2B kimono private experiment, step A).

Headless only:
  blender -b -P b2_import_split.py -- build      -> imports the GLB, orients/scales/splits, analyses, saves the base blend
  blender -b <base.blend> -P b2_import_split.py -- render [names...]   -> renders from the SAVED blend (proves reopen)

Source (read-only): References/Characters/2B_kimono_private/source/28.glb
Writes only into WorkFiles/Characters/2B_private/.
"""
import bpy, bmesh, sys, os, json, math, time
from collections import defaultdict
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

SRC = r"C:/Users/Cody/Desktop/Blender_Projects/References/Characters/2B_kimono_private/source/28.glb"
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/Characters/2B_private"
BLEND = OUT + "/2B_private_base.blend"
RENDERS = OUT + "/renders"
ANALYSIS = OUT + "/stepA_build_analysis.json"
BODY_HEIGHT = 1.68
WELD_DIST = 1e-9  # metres: exact duplicates only (larger tolerances collapse real 3-micron nail/toe edges)

# source material -> (layer, short name). Verified visually in step A (see stepA_report.json issues).
CLASS = {
    "Body": ("BODY", "Body"), "Face": ("BODY", "Face"), "Lips": ("BODY", "Lips"), "Teeth": ("BODY", "Teeth"),
    "Head": ("BODY", "Head"), "Ears": ("BODY", "Ears"), "Legs": ("BODY", "Legs"), "EyeSocket": ("BODY", "EyeSocket"),
    "Mouth": ("BODY", "Mouth"), "Arms": ("BODY", "Arms"), "Pupils": ("BODY", "Pupils"),
    "EyeMoisture": ("BODY", "EyeMoisture"), "Fingernails": ("BODY", "Fingernails"), "Cornea": ("BODY", "Cornea"),
    "Irises": ("BODY", "Irises"), "Sclera": ("BODY", "Sclera"), "Toenails": ("BODY", "Toenails"), "Tear": ("BODY", "Tear"),
    "7_-mask.face_eyeslashes_0.15_0_0": ("BODY", "Eyelashes"),
    "27_haira_0.15_0_0": ("HAIR", "HairA"), "27_hairb_0.15_0_0": ("HAIR", "HairB"),
    "Upper": ("CLO", "Upper"), "Sleeve": ("CLO", "Sleeve"), "SleeveIn": ("CLO", "SleeveIn"), "LowerIn": ("CLO", "LowerIn"),
    "LowerEdge": ("CLO", "LowerEdge"), "UpperEdge02": ("CLO", "UpperEdge02"), "Belt": ("CLO", "Belt"),
    "LowerOut": ("CLO", "LowerOut"), "UpEdge01": ("CLO", "UpEdge01"),
    "24_outfit_a_1.2_0_0": ("CLO", "Headband"),
    "24_+mask.outfit_b_1.2_0_0": ("CLO", "Blindfold"),
    "24_outfit_a_1.2_0_0_2B_Boots": ("CLO", "Boots"),
    "24_outfit_a_1.2_0_0_2B_Underware": ("CLO", "Underwear"),
}
LAYER_COLL = {"BODY": "Body", "HAIR": "Hair", "CLO": "Clothing"}
# skin surfaces used for the 1.68 m height and the body-shell checks
SKIN = ["Body", "Face", "Lips", "Head", "Ears", "Legs", "Arms", "Fingernails", "Toenails", "EyeSocket"]
SHELL = SKIN + ["Mouth"]
EYE_FIX = {"Cornea": (0.12, 0.05), "EyeMoisture": (0.05, 0.05), "Tear": (0.05, 0.1)}
UNSUB_TARGETS = ["Body", "Arms", "Legs", "Face", "Head", "SkinShell"]
UNSUB_ITERS = (1, 2, 4)  # Blender counts half-levels: 2 iterations undo one Catmull-Clark level


def log(*a):
    print("[b2]", *a, flush=True)


def tris_of(me):
    import numpy as np
    n = len(me.polygons)
    lt = [0] * n
    me.polygons.foreach_get("loop_total", lt)
    return int(sum(lt)) - 2 * n


def poly_hist(me):
    h = defaultdict(int)
    for p in me.polygons:
        h[len(p.vertices)] += 1
    return {str(k): v for k, v in sorted(h.items())}


def world_coords(o):
    mw = o.matrix_world
    return [mw @ v.co for v in o.data.vertices]


def bbox_of(objs):
    mn = Vector((1e9, 1e9, 1e9)); mx = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for c in world_coords(o):
            for k in range(3):
                mn[k] = min(mn[k], c[k]); mx[k] = max(mx[k], c[k])
    return mn, mx


def get_coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


# ----------------------------------------------------------------------------------------------------------- analyses
def boundary_loops(bm, label_layer=None, names=None):
    """Group boundary edges into connected loops; return list of dicts."""
    bm.edges.ensure_lookup_table()
    parent = {}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    bedges = [e for e in bm.edges if e.is_boundary]
    for e in bedges:
        for v in e.verts:
            parent.setdefault(v.index, v.index)
        a, b = find(e.verts[0].index), find(e.verts[1].index)
        if a != b:
            parent[a] = b
    groups = defaultdict(list)
    for e in bedges:
        groups[find(e.verts[0].index)].append(e)
    out = []
    for g in groups.values():
        vs = {v for e in g for v in e.verts}
        cs = [v.co for v in vs]
        c = sum(cs, Vector()) / len(cs)
        mn = Vector([min(p[k] for p in cs) for k in range(3)]); mx = Vector([max(p[k] for p in cs) for k in range(3)])
        length = sum(e.calc_length() for e in g)
        srcs = defaultdict(int)
        if label_layer is not None:
            for e in g:
                for f in e.link_faces:
                    srcs[names[f[label_layer]]] += 1
        out.append({"edges": len(g), "perimeter_m": round(length, 4), "centroid": [round(x, 4) for x in c],
                    "size_m": [round(x, 4) for x in (mx - mn)], "surfaces": dict(srcs)})
    out.sort(key=lambda d: -d["perimeter_m"])
    return out


def cluster_faces(bm, fset):
    """Connected components (via shared verts) of a set of faces."""
    seen = set(); comps = []
    for f in fset:
        if f.index in seen:
            continue
        stack = [f]; comp = []; seen.add(f.index)
        while stack:
            g = stack.pop(); comp.append(g)
            for v in g.verts:
                for h in v.link_faces:
                    if h.index not in seen and h in fset:
                        seen.add(h.index); stack.append(h)
        comps.append(comp)
    comps.sort(key=lambda c: -len(c))
    return comps


def region_name(c, h=BODY_HEIGHT):
    z = c[2] / h; x = c[0]
    side = "L" if x > 0.02 else ("R" if x < -0.02 else "C")
    if z > 0.87: r = "head"
    elif z > 0.81: r = "neck"
    elif z > 0.70: r = "chest/shoulders"
    elif z > 0.60: r = "waist/belly"
    elif z > 0.50: r = "hips/pelvis"
    elif z > 0.30: r = "thigh/knee"
    elif z > 0.06: r = "shin/calf"
    else: r = "foot"
    if abs(x) > 0.25 and z > 0.45:
        r = "arm/hand"
    return f"{r} ({side})"


def exact_weld(bm, dist=None):
    """Weld coincident vertices without ever collapsing an edge (face count stays identical)."""
    dup = bmesh.ops.find_doubles(bm, verts=bm.verts, dist=WELD_DIST if dist is None else dist)["targetmap"]
    tm = {v: t for v, t in dup.items() if not any(t in e.verts for e in v.link_edges)}
    bmesh.ops.weld_verts(bm, targetmap=tm)
    return len(tm)


def pair_quads(bm):
    """The GLB stores every source quad as two consecutive triangles; dissolve each pair's shared edge."""
    bm.faces.ensure_lookup_table()
    n = len(bm.faces) // 2
    diag = []; bad = 0
    for k in range(n):
        a = bm.faces[2 * k]; b = bm.faces[2 * k + 1]
        sh = [e for e in a.edges if b in e.link_faces]
        if len(sh) == 1 and len(a.verts) == 3 and len(b.verts) == 3:
            diag.append(sh[0])
        else:
            bad += 1
    bmesh.ops.dissolve_edges(bm, edges=diag, use_verts=False, use_face_split=False)
    return {"pairs": n, "paired": len(diag), "unpaired": bad + (len(bm.faces) % 2)}


def island_normalise(b, uv, ratios):
    """3D-area/UV-area ratio divided by the median of its UV island (UV islands have different texel scales)."""
    from bpy_extras import bmesh_utils
    norm = [1.0] * len(ratios)
    for isl in bmesh_utils.bmesh_linked_uv_islands(b, uv):
        rs = sorted(ratios[f.index] for f in isl if ratios[f.index] == ratios[f.index])
        if len(rs) < 30:
            continue
        m = rs[len(rs) // 2]
        for f in isl:
            r = ratios[f.index]
            norm[f.index] = r / m if r == r and m > 0 else 1.0
    return norm


def skin_analysis(objs_by_short, clo_objs):
    res = {}
    # per-object boundary loops
    per = {}
    for short, o in objs_by_short.items():
        bm = bmesh.new(); bm.from_mesh(o.data)
        loops = boundary_loops(bm)
        per[o.name] = {"open_loops": len(loops), "boundary_edges": sum(l["edges"] for l in loops),
                       "largest": loops[:3]}
        bm.free()
    res["per_object"] = per
    # combined shell
    names = []
    bm = bmesh.new()
    lay = None
    for short in SHELL:
        o = objs_by_short.get(short)
        if not o:
            continue
        n0 = len(bm.faces)
        bm.from_mesh(o.data)
        lay = bm.faces.layers.int.get("src") or bm.faces.layers.int.new("src")
        bm.faces.ensure_lookup_table()
        for f in bm.faces[n0:]:
            f[lay] = len(names)
        names.append(o.name)
    exact_weld(bm)
    bm.verts.index_update(); bm.edges.index_update(); bm.faces.index_update()
    loops = boundary_loops(bm, lay, names)
    for l in loops:
        l["region"] = region_name(l["centroid"])
    res["shell_surfaces"] = names
    res["shell_open_loops"] = len(loops)
    res["shell_loops"] = loops[:40]
    nm = [e for e in bm.edges if len(e.link_faces) > 2]
    res["shell_nonmanifold_edges"] = len(nm)

    # self intersections of the skin (excluding mouth interior)
    t0 = time.time()
    skin_faces = [f for f in bm.faces if names[f[lay]] != objs_by_short["Mouth"].name]
    bm2 = bmesh.new()
    vmap = {}
    for f in skin_faces:
        vs = []
        for v in f.verts:
            if v.index not in vmap:
                vmap[v.index] = bm2.verts.new(v.co)
            vs.append(vmap[v.index])
        try:
            bm2.faces.new(vs)
        except ValueError:
            pass
    bm2.verts.ensure_lookup_table(); bm2.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm2)
    pairs = tree.overlap(tree)
    fverts = [set(v.index for v in f.verts) for f in bm2.faces]
    bad = set()
    for i, j in pairs:
        if i == j or fverts[i] & fverts[j]:
            continue
        bad.add(i); bad.add(j)
    badf = {bm2.faces[i] for i in bad}
    comps = cluster_faces(bm2, badf)
    si = []
    for comp in comps[:25]:
        cs = [f.calc_center_median() for f in comp]
        c = sum(cs, Vector()) / len(cs)
        si.append({"faces": len(comp), "centroid": [round(x, 4) for x in c], "region": region_name(c)})
    res["self_intersection_faces"] = len(bad)
    res["self_intersection_clusters"] = si
    res["self_intersection_secs"] = round(time.time() - t0, 1)
    bm2.free()

    # compression / stretch via 3D-area / UV-area ratio (per surface normalised by median)
    clo_bm = bmesh.new()
    for o in clo_objs:
        clo_bm.from_mesh(o.data)
    clo_tree = BVHTree.FromBMesh(clo_bm)
    crush = []
    stretch_stats = {}
    for short in ["Body", "Legs", "Arms", "Head", "Face", "Ears", "Lips"]:
        o = objs_by_short[short]
        b = bmesh.new(); b.from_mesh(o.data)
        uv = b.loops.layers.uv.active
        b.faces.ensure_lookup_table()
        ratios = []
        for f in b.faces:
            l = f.loops
            a = l[0][uv].uv; bb = l[1][uv].uv; cc = l[2][uv].uv
            auv = abs((bb - a).cross(cc - a)) * 0.5
            a3 = f.calc_area()
            ratios.append(a3 / auv if auv > 1e-12 else float('nan'))
        good = sorted(r for r in ratios if r == r)
        med = good[len(good) // 2]
        norm = island_normalise(b, uv, ratios)
        low = {b.faces[i] for i, r in enumerate(norm) if r < 0.30}
        high = {b.faces[i] for i, r in enumerate(norm) if r > 3.0}
        stretch_stats[o.name] = {"median_area_per_uv": med, "faces_below_0.30": len(low), "faces_above_3.0": len(high)}
        for kind, fs in (("compressed", low), ("stretched", high)):
            for comp in cluster_faces(b, fs):
                if len(comp) < 12:
                    continue
                cs = [f.calc_center_median() for f in comp]
                c = sum(cs, Vector()) / len(cs)
                loc, nrm, idx, dist = clo_tree.find_nearest(c)
                crush.append({"object": o.name, "kind": kind, "faces": len(comp), "centroid": [round(x, 4) for x in c],
                              "region": region_name(c),
                              "mean_ratio": round(sum(norm[f.index] for f in comp) / len(comp), 3),
                              "dist_to_clothing_m": round(dist, 4) if dist is not None else None})
        b.free()
    crush.sort(key=lambda d: -d["faces"])
    res["area_ratio_stats"] = stretch_stats
    res["area_ratio_clusters"] = crush[:40]
    clo_bm.free()
    bm.free()
    return res


def unsubdiv_test(objs_by_short, coll):
    out = {}
    dg = bpy.context.evaluated_depsgraph_get()
    UNSUB_TARGETS_ = UNSUB_TARGETS
    # whole welded skin shell (DAZ subdivided the figure as one mesh, so surface borders are not real borders)
    shell_me = bpy.data.meshes.new("TEST_SkinShell_src")
    bm = bmesh.new()
    for s_ in SHELL:
        n0 = len(bm.faces)
        tmpb = bmesh.new(); tmpb.from_mesh(objs_by_short[s_].data)
        pair_quads(tmpb)  # quadify per surface first (the weld may reorder faces)
        sl = tmpb.faces.layers.int.get("src") or tmpb.faces.layers.int.new("src")
        for f in tmpb.faces:
            f[sl] = SHELL.index(s_)
        tmpb.to_mesh(shell_me); tmpb.free()
        bm.from_mesh(shell_me)
    exact_weld(bm)
    bm.to_mesh(shell_me); bm.free()
    shell_obj = bpy.data.objects.new("TEST_SkinShell_src", shell_me)
    objs_by_short = dict(objs_by_short); objs_by_short["SkinShell"] = shell_obj
    for short in UNSUB_TARGETS:
        src = objs_by_short[short]
        r = {"orig_verts": len(src.data.vertices), "orig_faces": len(src.data.polygons), "orig_poly_sizes": poly_hist(src.data)}
        # quadify copy (the GLB is fully triangulated; each source quad = 2 consecutive triangles)
        me = src.data.copy(); me.name = f"TEST_{short}_quads"
        bm = bmesh.new(); bm.from_mesh(me)
        if all(len(f.verts) == 4 for f in bm.faces):
            r["quad_pairing"] = "already quads (paired per surface before welding)"
        else:
            r["quad_pairing"] = pair_quads(bm)
        bm.to_mesh(me); bm.free()
        q = bpy.data.objects.new(me.name, me); coll.objects.link(q)
        q["src_material"] = src.get("src_material", ""); q["b2_test"] = "quadified copy of " + src.name
        r["quads_verts"] = len(me.vertices); r["quads_faces"] = len(me.polygons); r["quads_poly_sizes"] = poly_hist(me)
        # un-subdivide copies
        for it in UNSUB_ITERS:
            tmp = bpy.data.objects.new(f"tmp_{short}_{it}", me); coll.objects.link(tmp)
            m = tmp.modifiers.new("unsub", 'DECIMATE'); m.decimate_type = 'UNSUBDIV'; m.iterations = it
            dg.update()
            ev = tmp.evaluated_get(dg)
            nm = bpy.data.meshes.new_from_object(ev); nm.name = f"TEST_{short}_unsub{it}"
            bpy.data.objects.remove(tmp)
            u = bpy.data.objects.new(nm.name, nm); coll.objects.link(u)
            u["b2_test"] = f"Decimate UNSUBDIV x{it} of TEST_{short}_quads"
            r[f"unsub{it}"] = unsub_metrics(nm, len(me.vertices), it / 2)
        # raw (triangulated) control
        if short == "Body":
            tmp = bpy.data.objects.new("tmp_raw", src.data.copy()); coll.objects.link(tmp)
            m = tmp.modifiers.new("unsub", 'DECIMATE'); m.decimate_type = 'UNSUBDIV'; m.iterations = 1
            dg.update(); ev = tmp.evaluated_get(dg)
            nm = bpy.data.meshes.new_from_object(ev)
            r["raw_tris_unsub1"] = unsub_metrics(nm, len(src.data.vertices), 1)
            d = tmp.data
            bpy.data.objects.remove(tmp); bpy.data.meshes.remove(d); bpy.data.meshes.remove(nm)
        out[src.name if short != "SkinShell" else "SkinShell(" + "+".join(SHELL) + ")"] = r
        log("unsub", short, json.dumps({k: v for k, v in r.items() if k.startswith("unsub")}))
    dense = bmesh.new(); dense.from_mesh(bpy.data.objects["TEST_SkinShell_quads"].data)
    out["exact_topological"] = topo_unsubdiv_shell(bpy.data.objects["TEST_SkinShell_quads"].data, coll, dense)
    dense.free()
    log("exact", json.dumps(out["exact_topological"]))
    return out


# ----------------------------------------------------------------------------------------------------------- exact un-subdivide
def topo_unsub_level(bm, uvname="UVMap"):
    """Invert one Catmull-Clark level topologically on a closed all-quad mesh.
    Classes: V (old verts), E (edge points), F (face points). Edges join E to V/F (bipartite); quad diagonals join V to F.
    Irregular (valence != 4) verts are V. Returns new bmesh (V verts, one face per F vert) + stats.
    Positions: CC vertex rule inverted by Jacobi iteration  S = (n V' - Q - avg(N)) / (n - 2)."""
    from collections import deque
    bm.verts.ensure_lookup_table(); bm.verts.index_update(); bm.faces.index_update()
    uv = bm.loops.layers.uv.get(uvname)
    src = bm.faces.layers.int.get("src")
    nv = len(bm.verts)
    col = [-1] * nv
    for s0 in bm.verts:
        if col[s0.index] >= 0:
            continue
        col[s0.index] = 0; dq = deque([s0])
        while dq:
            v = dq.popleft()
            for e in v.link_edges:
                w = e.other_vert(v)
                if col[w.index] < 0:
                    col[w.index] = 1 - col[v.index]; dq.append(w)
    irr = [v for v in bm.verts if len(v.link_edges) != 4]
    xc = col[irr[0].index]
    stats = {"irregular": len(irr), "irregular_all_same_class": all(col[v.index] == xc for v in irr)}
    # diagonal colouring inside class X
    dcol = [-1] * nv
    ambiguous = 0
    seeds = irr + [v for v in bm.verts if col[v.index] == xc]
    for s0 in seeds:
        if dcol[s0.index] >= 0:
            continue
        if len(s0.link_edges) == 4 and s0 not in irr:
            ambiguous += 1
        dcol[s0.index] = 0; dq = deque([s0])
        while dq:
            v = dq.popleft()
            for l in v.link_loops:
                w = l.link_loop_next.link_loop_next.vert
                if dcol[w.index] < 0:
                    dcol[w.index] = 1 - dcol[v.index]; dq.append(w)
    stats["components_without_irregular_seed"] = ambiguous
    stats["irregular_all_V"] = all(dcol[v.index] == 0 for v in irr)
    Vs = [v for v in bm.verts if col[v.index] == xc and dcol[v.index] == 0]
    Fs = [v for v in bm.verts if col[v.index] == xc and dcol[v.index] == 1]
    nb = bmesh.new()
    nuv = nb.loops.layers.uv.new(uvname) if uv else None
    nsrc = nb.faces.layers.int.new("src")
    vmap = {}
    for v in Vs:
        vmap[v.index] = nb.verts.new(v.co)
    fpos = {}  # base face -> face point position
    bad = 0; flipped = 0
    for f in Fs:
        l0 = f.link_loops[0]; l = l0; ring = []
        for _ in range(32):
            ring.append(l)
            l = l.link_loop_prev.link_loop_radial_next
            if l == l0:
                break
        corners = [x.link_loop_next.link_loop_next for x in ring]
        try:
            vs = [vmap[c.vert.index] for c in corners]
            nf = nb.faces.new(vs)
        except (KeyError, ValueError):
            bad += 1
            continue
        if uv:
            for c, nl in zip(corners, nf.loops):
                nl[nuv].uv = c[uv].uv
        avgn = sum((x.face.normal for x in ring), Vector())
        nf.normal_update()
        if nf.normal.dot(avgn) < 0:
            flipped += 1  # geometric disagreement only (winding comes from topology, consistent by construction)
        if src:
            nf[nsrc] = ring[0].face[src]
        fpos[nf] = f.co.copy()
    if flipped > len(nb.faces) / 2:
        for nf in nb.faces:
            nf.normal_flip()
        flipped = len(nb.faces) - flipped
    stats.update({"V": len(Vs), "F": len(Fs), "faces_failed": bad, "faces_normal_disagree_with_dense": flipped})
    # invert the vertex rule
    nb.verts.ensure_lookup_table(); nb.verts.index_update()
    Vp = [v.co.copy() for v in nb.verts]
    Q = []; N = []
    for v in nb.verts:
        fs = v.link_faces
        Q.append(sum((fpos[x] for x in fs), Vector()) / max(len(fs), 1))
        N.append([e.other_vert(v).index for e in v.link_edges])
    S = [p.copy() for p in Vp]
    for it in range(60):
        S2 = []
        for i, p in enumerate(Vp):
            n = len(N[i])
            if n < 3 or any(e.is_boundary for e in nb.verts[i].link_edges):
                S2.append(p); continue
            an = sum((S[j] for j in N[i]), Vector()) / n
            tgt = (n * p - Q[i] - an) / (n - 2)
            S2.append(S[i].lerp(tgt, 0.6))
        S = S2
    for v, p in zip(nb.verts, S):
        v.co = p
    return nb, stats


def topo_unsubdiv_shell(shell_quads_me, coll, dense_bm):
    out = {}
    bm = bmesh.new(); bm.from_mesh(shell_quads_me)
    base_counts = {"L2_input": {"verts": len(bm.verts), "faces": len(bm.faces)}}
    levels = []
    cur = bm
    for lvl in (1, 2):
        nb, st = topo_unsub_level(cur)
        me = bpy.data.meshes.new(f"TEST_SkinShell_exact{lvl}")
        nb.to_mesh(me)
        o = bpy.data.objects.new(me.name, me); coll.objects.link(o)
        o["b2_test"] = f"exact topological Catmull-Clark un-subdivide x{lvl} of the welded skin shell (vertex rule inverted)"
        st["verts"] = len(nb.verts); st["faces"] = len(nb.faces); st["poly_sizes"] = poly_hist(me)
        st["vert_ratio_vs_input"] = round(len(nb.verts) / len(bm.verts), 4)
        st["nonmanifold_edges"] = sum(1 for e in nb.edges if len(e.link_faces) != 2)
        out[f"exact{lvl}"] = st
        levels.append(o)
        if cur is not bm:
            cur.free()
        cur = nb
    cur.free(); bm.free()
    # validation: re-subdivide the base with Subsurf and measure the distance back to the dense GLB shell
    tree = BVHTree.FromBMesh(dense_bm)
    dg = bpy.context.evaluated_depsgraph_get()
    for o, lv in ((levels[0], 1), (levels[1], 2)):
        for lim in (False, True):
            m = o.modifiers.new("chk", 'SUBSURF'); m.levels = lv; m.render_levels = lv; m.use_limit_surface = lim
            dg.update()
            ev = o.evaluated_get(dg); me2 = ev.to_mesh()
            ds = []
            for v in me2.vertices:
                loc, nrm, idx, d = tree.find_nearest(v.co)
                ds.append(d or 0.0)
            ds.sort()
            out[f"exact{lv}_resubdiv_limit{int(lim)}"] = {
                "verts": len(me2.vertices), "dense_verts": len(dense_bm.verts),
                "mean_mm": round(1000 * sum(ds) / len(ds), 4), "p95_mm": round(1000 * ds[int(0.95 * len(ds))], 4),
                "max_mm": round(1000 * ds[-1], 4)}
            ev.to_mesh_clear()
            o.modifiers.remove(m)
    return out


def unsub_metrics(me, base_verts, it):
    bm = bmesh.new(); bm.from_mesh(me)
    val = defaultdict(int)
    for v in bm.verts:
        val[len(v.link_edges)] += 1
    nonman = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    wire = sum(1 for e in bm.edges if len(e.link_faces) == 0)
    degen = sum(1 for f in bm.faces if f.calc_area() < 1e-10)
    hi = sum(n for k, n in val.items() if k >= 7)
    tris = [f for f in bm.faces if len(f.verts) == 3]
    tri_border = sum(1 for f in tris if any(e.is_boundary for e in f.edges) or any(v.is_boundary for v in f.verts))
    irregular = sum(1 for v in bm.verts if not v.is_boundary and len(v.link_edges) != 4)
    nv = len(bm.verts); nf = len(bm.faces)
    bm.free()
    ph = poly_hist(me)
    quads = ph.get("4", 0)
    return {"verts": nv, "faces": nf, "vert_ratio": round(nv / base_verts, 4), "expected_ratio": round(0.25 ** it, 4),
            "poly_sizes": ph, "quad_fraction": round(quads / max(nf, 1), 4), "valence_ge7_verts": hi,
            "nonmanifold_edges": nonman, "wire_edges": wire, "degenerate_faces": degen,
            "tris_touching_border": tri_border, "interior_irregular_verts": irregular,
            "valence_hist": {str(k): v for k, v in sorted(val.items())}}


# ----------------------------------------------------------------------------------------------------------- build
def build():
    t0 = time.time()
    assert not os.path.exists(BLEND) or os.environ.get("B2_OVERWRITE") == "1", "refusing to overwrite " + BLEND
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 1.0; sc.unit_settings.length_unit = 'METERS'
    bpy.ops.import_scene.gltf(filepath=SRC, merge_vertices=True, import_scene_as_collection=False)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    assert len(meshes) == 1, meshes
    obj = meshes[0]
    for o in list(bpy.data.objects):
        if o is not obj and o.type == 'EMPTY':
            pass
    me = obj.data
    info = {"import": {"object": obj.name, "verts_after_merge": len(me.vertices), "tris": tris_of(me),
                       "matrix_world_at_import": [list(r) for r in obj.matrix_world]}}
    # bake object transform into data
    if obj.parent:
        mw = obj.matrix_world.copy(); obj.parent = None; obj.matrix_world = mw
    me.transform(obj.matrix_world); obj.matrix_world = Matrix.Identity(4)
    mats = [m.name for m in me.materials]
    idx = {n: i for i, n in enumerate(mats)}
    missing = [n for n in mats if n not in CLASS]
    assert not missing, missing

    # vertex sets per material
    vby = defaultdict(set)
    for p in me.polygons:
        vby[p.material_index].update(p.vertices)

    def pts(names):
        s = set()
        for n in names:
            s |= vby[idx[n]]
        return [me.vertices[i].co.copy() for i in s]

    # yaw from torso PCA (widest horizontal axis = left/right) and from the irises
    tor = pts(["Body"])
    cx = sum(p.x for p in tor) / len(tor); cy = sum(p.y for p in tor) / len(tor)
    sxx = sum((p.x - cx) ** 2 for p in tor); syy = sum((p.y - cy) ** 2 for p in tor); sxy = sum((p.x - cx) * (p.y - cy) for p in tor)
    ang_torso = 0.5 * math.atan2(2 * sxy, sxx - syy)  # major axis angle from +X
    iris = pts(["Irises"])
    mx_ = sum(p.x for p in iris) / len(iris)
    a = [p for p in iris if p.x > mx_]; b = [p for p in iris if p.x <= mx_]
    ca = sum(a, Vector()) / len(a); cb = sum(b, Vector()) / len(b)
    ang_eyes = math.atan2(ca.y - cb.y, ca.x - cb.x)
    yaw = -ang_torso
    R = Matrix.Rotation(yaw, 4, 'Z')
    me.transform(R)
    # facing: face must be at -Y relative to the head
    face = pts(["Face"]); head = pts(["Head"])
    fy = sum(p.y for p in face) / len(face); hy = sum(p.y for p in head) / len(head)
    flip = fy > hy
    if flip:
        me.transform(Matrix.Rotation(math.pi, 4, 'Z'))
    info["orient"] = {"torso_axis_deg": round(math.degrees(ang_torso), 3), "eye_axis_deg": round(math.degrees(ang_eyes), 3),
                      "applied_yaw_deg": round(math.degrees(yaw) + (180 if flip else 0), 3), "flipped_180": flip}
    # scale to 1.68 m skin height
    skin = pts(SKIN)
    zmin = min(p.z for p in skin); zmax = max(p.z for p in skin)
    s = BODY_HEIGHT / (zmax - zmin)
    me.transform(Matrix.Scale(s, 4))
    tor = pts(["Body"])
    cx = (min(p.x for p in tor) + max(p.x for p in tor)) / 2; cy = (min(p.y for p in tor) + max(p.y for p in tor)) / 2
    boots = pts(["24_outfit_a_1.2_0_0_2B_Boots"])
    bz = min(p.z for p in boots)
    me.transform(Matrix.Translation((-cx, -cy, -bz)))
    skin = pts(SKIN)
    info["scale"] = {"raw_skin_height": round(zmax - zmin, 6), "scale_factor": s,
                     "skin_zmin": min(p.z for p in skin), "skin_zmax": max(p.z for p in skin),
                     "centre_from": "torso (BODY_Body) bbox centre X/Y"}
    # soles
    feet = [p for p in pts(["Legs", "Toenails"]) if p.z < 0.15]
    footinfo = {}
    for side, cond in (("L(+X)", lambda p: p.x > 0), ("R(-X)", lambda p: p.x <= 0)):
        f = [p for p in feet if cond(p)]
        if not f:
            continue
        ymin = min(p.y for p in f); ymax = max(p.y for p in f)
        toe = [p for p in f if p.y < ymin + 0.25 * (ymax - ymin)]
        heel = [p for p in f if p.y > ymax - 0.25 * (ymax - ymin)]
        footinfo[side] = {"lowest_z": round(min(p.z for p in f), 4), "toe_region_lowest_z": round(min(p.z for p in toe), 4),
                          "heel_region_lowest_z": round(min(p.z for p in heel), 4), "foot_len_y": round(ymax - ymin, 4)}
    info["feet"] = footinfo

    # ---- separate by material
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.mode_set(mode='OBJECT')
    parts = [o for o in bpy.data.objects if o.type == 'MESH']
    colls = {k: get_coll(v) for k, v in LAYER_COLL.items()}
    objs_by_short = {}; rows = []
    for o in parts:
        used = {p.material_index for p in o.data.polygons}
        assert len(used) == 1, (o.name, used)
        mat = o.data.materials[used.pop()]
        layer, short = CLASS[mat.name]
        o.data.materials.clear(); o.data.materials.append(mat)
        o.data.polygons.foreach_set("material_index", [0] * len(o.data.polygons))
        name = f"{layer}_{short}"
        o.name = name; o.data.name = name
        o["src_material"] = mat.name
        for c in list(o.users_collection):
            c.objects.unlink(o)
        colls[layer].objects.link(o)
        objs_by_short[short] = o
        rows.append({"name": name, "layer": LAYER_COLL[layer], "materials": [mat.name], "tris": tris_of(o.data),
                     "verts": len(o.data.vertices)})
    # weld the BODY surfaces: the GLB splits vertices along almost every edge (glTF merge only joins identical
    # attributes), which leaves thousands of fake open edges. Corner data (UVs, normals) is kept per loop.
    weld = {}
    for short, o in objs_by_short.items():
        if not o.name.startswith("BODY_"):
            continue
        bm = bmesh.new(); bm.from_mesh(o.data)
        v0 = len(bm.verts)
        exact_weld(bm)
        bm.to_mesh(o.data); bm.free()
        weld[o.name] = {"verts_before": v0, "verts_after": len(o.data.vertices), "tris_after": tris_of(o.data)}
    info["weld"] = {"dist_m": WELD_DIST, "objects": weld}
    # eye covers: the GLB gives Cornea/EyeMoisture/Tear alpha 0.995 (BLEND), which renders the eyes solid white
    eyefix = {}
    for short, (alpha, rough) in EYE_FIX.items():
        m = objs_by_short[short].active_material
        b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        m["b2_src_alpha"] = b.inputs["Alpha"].default_value
        m["b2_src_roughness"] = b.inputs["Roughness"].default_value
        b.inputs["Alpha"].default_value = alpha
        b.inputs["Roughness"].default_value = rough
        m["b2_fix"] = f"alpha {m['b2_src_alpha']:.3f}->{alpha}, roughness ->{rough} (source rendered the eyes white)"
        eyefix[m.name] = m["b2_fix"]
    info["material_fixes"] = eyefix
    for r in rows:
        o = bpy.data.objects[r["name"]]
        r["tris"] = tris_of(o.data); r["verts"] = len(o.data.vertices)
    rows.sort(key=lambda r: (["Body", "Hair", "Clothing"].index(r["layer"]), r["name"]))
    info["objects"] = rows
    info["total_tris"] = sum(r["tris"] for r in rows)
    log("total tris", info["total_tris"])
    # bboxes
    lay_bb = {}
    for layer, cname in LAYER_COLL.items():
        mn, mx = bbox_of(list(bpy.data.collections[cname].objects))
        lay_bb[cname] = {"min": [round(x, 4) for x in mn], "max": [round(x, 4) for x in mx]}
    info["layer_bbox"] = lay_bb
    for short in ("Boots", "Headband", "Blindfold", "Eyelashes", "Underwear"):
        mn, mx = bbox_of([objs_by_short[short]])
        info.setdefault("piece_bbox", {})[short] = {"min": [round(x, 4) for x in mn], "max": [round(x, 4) for x in mx]}

    # ---- analyses
    clo = list(bpy.data.collections["Clothing"].objects)
    info["body_integrity"] = skin_analysis(objs_by_short, [o for o in clo if o.name != "CLO_Underwear"])
    tcoll = get_coll("Test_Unsubdiv")
    info["unsubdiv"] = unsubdiv_test(objs_by_short, tcoll)
    tcoll.hide_render = True
    tcoll.hide_viewport = True

    build_rig()
    # images: keep them packed inside the .blend (they come packed from the GLB)
    info["images"] = [{"name": im.name, "size": list(im.size), "packed": im.packed_file is not None} for im in bpy.data.images]
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    info["blend"] = BLEND
    info["build_secs"] = round(time.time() - t0, 1)
    with open(ANALYSIS, "w") as fh:
        json.dump(info, fh, indent=1)
    log("saved", BLEND, "secs", info["build_secs"])


# ----------------------------------------------------------------------------------------------------------- render rig
def build_rig():
    sc = bpy.context.scene
    rig = get_coll("Render_Rig")
    # floor disc (light grey)
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, radius=12.0, segments=64)
    fme = bpy.data.meshes.new("RIG_Floor"); bm.to_mesh(fme); bm.free()
    floor = bpy.data.objects.new("RIG_Floor", fme); rig.objects.link(floor)
    fm = bpy.data.materials.new("RIG_Floor_Grey")
    bsdf = next(n for n in fm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Base Color"].default_value = (0.62, 0.62, 0.62, 1); bsdf.inputs["Roughness"].default_value = 0.8
    fme.materials.append(fm)
    # world: soft sky gradient (zenith blue-grey -> horizon light grey)
    w = bpy.data.worlds.new("RIG_SoftSky"); sc.world = w
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.5; ramp.color_ramp.elements[0].color = (0.78, 0.78, 0.78, 1)
    ramp.color_ramp.elements[1].position = 1.0; ramp.color_ramp.elements[1].color = (0.55, 0.64, 0.78, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.6
    # 3-point lights (angles relative to the character facing -Y)
    def area(name, pos, energy, size, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.size = size; ld.color = color
        lo = bpy.data.objects.new(name, ld); rig.objects.link(lo)
        lo.location = pos
        d = Vector((0, 0, 1.0)) - Vector(pos)
        lo.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        return lo
    area("RIG_Key", (-2.2, -3.0, 2.8), 900, 2.0, (1.0, 0.97, 0.92))
    area("RIG_Fill", (3.0, -2.2, 1.6), 350, 3.0, (0.92, 0.96, 1.0))
    area("RIG_Rim", (1.2, 3.2, 2.6), 700, 1.5)
    cam_d = bpy.data.cameras.new("RIG_Camera"); cam_d.lens = 70; cam_d.clip_start = 0.05; cam_d.clip_end = 100
    cam = bpy.data.objects.new("RIG_Camera", cam_d); rig.objects.link(cam); sc.camera = cam
    r = sc.render
    try:
        r.engine = 'CYCLES'
    except TypeError as e:
        log("engine", e)
    r.resolution_x = 1000; r.resolution_y = 1400; r.resolution_percentage = 100
    r.film_transparent = False
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    sc.cycles.device = 'GPU'
    sc.cycles.max_bounces = 8; sc.cycles.transparent_max_bounces = 24
    try:
        sc.view_settings.view_transform = 'AgX'
    except TypeError:
        sc.view_settings.view_transform = 'Filmic'


# ----------------------------------------------------------------------------------------------------------- render
def enable_gpu():
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for t in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = t
            prefs.get_devices()
            ok = False
            for d in prefs.devices:
                d.use = d.type != 'CPU'
                ok = ok or d.use
            if ok:
                bpy.context.scene.cycles.device = 'GPU'
                log("GPU", t)
                return
        except Exception as e:
            log("gpu", t, e)
    bpy.context.scene.cycles.device = 'CPU'


def layer_objs(cname):
    return list(bpy.data.collections[cname].objects)


def set_visible(objs):
    vis = set(o.name for o in objs)
    for o in bpy.data.objects:
        if o.type == 'MESH' and (not o.name.startswith("RIG_") or o.name == "RIG_ModestyBand"):
            o.hide_render = o.name not in vis
    band = bpy.data.objects.get("RIG_ModestyBand")
    if band and "BODY_Body" in vis and "CLO_Upper" not in vis:
        band.hide_render = False  # body shown without the kimono -> cover the chest


def frame_camera(cam, center, direction, pts, margin=1.06):
    """Place a perspective camera looking along -direction at center so all pts fit."""
    sc = bpy.context.scene
    d = Vector(direction).normalized()
    rot = (-d).to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot.to_euler()
    R = rot.to_matrix()
    right = R @ Vector((1, 0, 0)); up = R @ Vector((0, 1, 0))
    cd = cam.data
    aspect = sc.render.resolution_x / sc.render.resolution_y
    sw = cd.sensor_width
    fov_w = 2 * math.atan(sw / 2 / cd.lens)  # sensor fit AUTO -> width on the larger side
    if aspect < 1:
        tan_v = math.tan(fov_w / 2); tan_h = tan_v * aspect
    else:
        tan_h = math.tan(fov_w / 2); tan_v = tan_h / aspect
    need = 0
    for p in pts:
        q = p - center
        x = q.dot(right); y = q.dot(up); z = q.dot(d)  # z = towards camera
        need = max(need, z + abs(x) * margin / tan_h, z + abs(y) * margin / tan_v)
    cam.location = center + d * need


def view_dir(view):
    ang = {"front": 0, "tq": 35, "side": 90, "back": 180}[view]
    a = math.radians(ang)
    # character faces -Y; its left is +X
    return Vector((math.sin(a), -math.cos(a), 0.0))


def bbox_pts(objs):
    mn, mx = bbox_of(objs)
    return [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)], (mn + mx) / 2


def render_to(path):
    bpy.context.scene.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    log("rendered", os.path.basename(path), round(time.time() - t, 1), "s")


def make_modesty_band():
    """Render-only neutral bandeau (not saved): the source underwear is bottoms only, so BODY renders stay tasteful."""
    src = bpy.data.objects["BODY_Body"]
    me = src.data
    cand = [v.co for v in me.vertices if 1.12 < v.co.z < 1.45 and abs(v.co.x) < 0.16]
    apex = min(cand, key=lambda c: c.y)
    z0, z1 = apex.z - 0.085, apex.z + 0.065
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not all(z0 < v.co.z < z1 for v in f.verts)], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * 0.004
    nm = bpy.data.meshes.new("RIG_ModestyBand"); bm.to_mesh(nm); bm.free()
    for a in list(nm.attributes):
        if a.name in ("custom_normal", "sharp_face"):
            nm.attributes.remove(a)
    o = bpy.data.objects.new("RIG_ModestyBand", nm)
    bpy.data.collections["Render_Rig"].objects.link(o)
    mat = bpy.data.materials.new("RIG_ModestyBand_Grey")
    b = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (0.09, 0.09, 0.095, 1); b.inputs["Roughness"].default_value = 0.65
    nm.materials.append(mat)
    sol = o.modifiers.new("thick", 'SOLIDIFY'); sol.thickness = 0.002; sol.offset = 1
    o.modifiers.new("smooth", 'SUBSURF').levels = 1
    for p in nm.polygons:
        p.use_smooth = True
    o.hide_render = True
    log("modesty band z", round(z0, 3), round(z1, 3))
    return o


def render(which):
    enable_gpu()
    sc = bpy.context.scene
    cam = sc.camera
    os.makedirs(RENDERS, exist_ok=True)
    body = layer_objs("Body"); hair = layer_objs("Hair"); clo = layer_objs("Clothing")
    band = make_modesty_band()
    under = [bpy.data.objects["CLO_Underwear"]]
    allv = body + hair + clo
    sets = {"full": allv, "body": body + under, "clothing": clo, "hair": hair}
    # full-body camera: fits everything, shared by full/body/clothing/hair so they overlay
    pts, c = bbox_pts(allv)
    c = Vector((c.x, c.y, c.z))
    for view in ("front", "tq", "side", "back"):
        for key, objs in sets.items():
            if key in ("clothing", "hair") and view == "back":
                continue
            name = f"{key}_{view}"
            if which and name not in which:
                continue
            if key == "hair":  # hair gets its own framing (tiny in the full-body camera)
                hp, hcen = bbox_pts(hair)
                frame_camera(cam, hcen, view_dir(view), hp, margin=1.25)
            else:
                frame_camera(cam, c, view_dir(view), pts)
            set_visible(objs)
            render_to(f"{RENDERS}/{name}.png")
    # face close-ups (body layer + hair; clothing off so the eyes show)
    mn, mx = bbox_of([bpy.data.objects["BODY_Irises"]])
    fmn, fmx = bbox_of([bpy.data.objects["BODY_Face"], bpy.data.objects["BODY_Ears"]])
    hc = Vector(((fmn.x + fmx.x) / 2, (fmn.y + fmx.y) / 2 + 0.02, (mn.z + mx.z) / 2 + 0.02))
    for view in ("front", "tq", "side"):
        for hair_on in (True, False):
            name = f"face_{view}_close" + ("" if hair_on else "_nohair")
            if not hair_on and view != "front":
                continue
            if which and name not in which:
                continue
            d = view_dir(view)
            q = (-d).to_track_quat('-Z', 'Y')
            cam.rotation_euler = q.to_euler()
            cam.location = hc + d * 0.62
            set_visible(body + under + (hair if hair_on else []))
            render_to(f"{RENDERS}/{name}.png")
    # diagnostic: bare feet (posed for the heels; right foot crushed in the boot)
    if not which or "diag_feet_close" in which:
        lg = bpy.data.objects["BODY_Legs"]
        fp = [v.co.copy() for v in lg.data.vertices if v.co.z < 0.2] + [v.co.copy() for v in bpy.data.objects["BODY_Toenails"].data.vertices]
        fmn = Vector([min(q[k] for q in fp) for k in range(3)]); fmx = Vector([max(q[k] for q in fp) for k in range(3)])
        fcen = (fmn + fmx) / 2
        box = [Vector((x, y, z)) for x in (fmn.x, fmx.x) for y in (fmn.y, fmx.y) for z in (fmn.z, fmx.z)]
        frame_camera(cam, fcen, Vector((0.45, -0.85, 0.2)), box, margin=1.15)
        set_visible(body + under)
        render_to(f"{RENDERS}/diag_feet_close.png")
    if not which or "unsubdiv_wire" in which:
        render_wire()


def render_wire():
    """Wire close-ups: face (front 3/4) and torso from the back (tasteful), original vs quadified vs best un-subdivided."""
    sc = bpy.context.scene
    cam = sc.camera
    tcoll = bpy.data.collections["Test_Unsubdiv"]
    tcoll.hide_render = False
    clay = bpy.data.materials.new("TMP_Clay")
    b = next(n for n in clay.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (0.72, 0.7, 0.68, 1); b.inputs["Roughness"].default_value = 0.7
    wire = bpy.data.materials.new("TMP_Wire")
    b = next(n for n in wire.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (0.02, 0.05, 0.12, 1); b.inputs["Roughness"].default_value = 0.5
    shell_names = ["BODY_" + x for x in SHELL]
    variants = {"original GLB (tris)": shell_names,
                "Blender UNSUBDIV x2": ["TEST_SkinShell_unsub2"],
                "exact un-subdiv L1": ["TEST_SkinShell_exact1"],
                "exact un-subdiv L0 (base)": ["TEST_SkinShell_exact2"]}
    thick = [0.00025, 0.0005, 0.0005, 0.0009]
    under = bpy.data.objects["CLO_Underwear"]
    sc.render.resolution_x = 700; sc.render.resolution_y = 700
    sc.cycles.samples = 48
    tmp_objs = []
    panels = []
    for vi, (label, names) in enumerate(variants.items()):
        objs = []
        for n in names:
            src = bpy.data.objects[n]
            o = bpy.data.objects.new("TMPW_" + n, src.data.copy())
            sc.collection.objects.link(o)
            o.data.materials.clear(); o.data.materials.append(clay); o.data.materials.append(wire)
            o.data.polygons.foreach_set("material_index", [0] * len(o.data.polygons))
            m = o.modifiers.new("wire", 'WIREFRAME')
            m.use_replace = False; m.material_offset = 1; m.use_even_offset = False  # even offset spikes on 3-micron nail edges
            m.thickness = thick[vi]
            objs.append(o); tmp_objs.append(o)
        set_visible(objs + [under])
        mn, mx = bbox_of([bpy.data.objects["BODY_Face"]])
        fc = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, (mn.z + mx.z) / 2))
        for part, (dirv, ctr, dist) in {"face": (view_dir("tq"), fc + Vector((0, 0, 0.005)), 0.62),
                                        "back": (view_dir("back"), Vector((0, 0.0, 1.20)), 1.75)}.items():
            d = dirv
            cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
            cam.location = ctr + d * dist
            p = f"{RENDERS}/_wire_{vi}_{part}.png"
            render_to(p)
            panels.append((label, part, p))
        for o in objs:
            o.hide_render = True
    with open(RENDERS + "/_wire_panels.json", "w") as fh:
        json.dump(panels, fh)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stage = argv[0] if argv else "build"
    if stage == "build":
        build()
    elif stage == "render":
        render(set(argv[1:]))
