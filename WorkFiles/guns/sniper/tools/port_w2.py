"""SR01 W2: port the SMG's proven W2 scripts into Scripts/guns/sniper (read-only use of Scripts/guns/smg)."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
src, dst = ROOT / 'Scripts/guns/smg', ROOT / 'Scripts/guns/sniper'


def port(a, b, extra=()):
    s = (src / a).read_text(encoding='utf-8')
    for x, y in extra:
        assert x in s, (a, x[:60])
        s = s.replace(x, y)
    for x, y in (('smg_surface', 'sr_surface'), ('smg_uvproj', 'sr_uvproj'), ('smg_lmpack', 'sr_lmpack'),
                 ('smg_uv1lib', 'sr_uv1lib'), ('SMG01', 'SR01'), ('Scripts/guns/smg/', 'Scripts/guns/sniper/'),
                 ('smg_', 'sr_')):
        s = s.replace(x, y)
    (dst / b).write_text(s, encoding='utf-8')
    print('ported', a, '->', b)


CONFIGS_OLD = '''    import smg_b3groups
    G = smg_b3groups.groups(None, None, None)
    out = {"rest": {}, "mag_out": {n: None for n in SS.MAG_PARTS}}
    for gname, g in G.items():
        lo, hi = g["range"]
        ends = [v for v in (lo, hi) if abs(v) > 1e-9]
        for v in ends:
            if g["kind"] == "slide":
                Mv = F.trans_matrix(g["axis"], v)
            else:
                Mv = F.rot_matrix(np.asarray(g["pivot"], float), g["axis"], v)
            mv = {}
            for pn, Mp in g.get("pre", {}).items():
                mv[pn] = np.asarray(Mp, float)
            for pn in g["parts"]:
                mv[pn] = Mv @ mv.get(pn, np.eye(4))
            out[f"{gname}@{v:g}"] = mv
    return out'''
CONFIGS_NEW = '''    # SR01: the sr_motion poses (frame M mm) as frame-B matrices on the part meshes' coordinates
    import sr_motion as MO
    out = {"rest": {}}
    if SS.TARGET != "gun":
        return out
    out["mag_out"] = {n: None for n in SS.MAG_PARTS}
    bones = {o.name: part_rec(o).get("bone") for o in bpy.data.collections[PARTS_COLL].objects if o.type == "MESH"}
    G = np.array(SS.GRIP_M, float)

    def toB(Mm):
        Tm, Tp = np.eye(4), np.eye(4)
        Tm[:3, 3], Tp[:3, 3] = -G, G
        return Tm @ Mm @ Tp

    def pose(fn):
        o = {}
        for n, b in bones.items():
            M = fn(b)
            if M is not None:
                o[n] = toB(M)
        return o
    out["bolt_open_back"] = pose(lambda b: MO.bolt(MO.BOLT_ROT, MO.BOLT_TRAVEL) if b == "bolt" else None)
    out["bolt_open"] = pose(lambda b: MO.bolt(MO.BOLT_ROT, 0.0) if b == "bolt" else None)
    out["trigger_pulled"] = pose(lambda b: MO.trigger(6.0) if b == "trigger" else None)
    out["safety_fire"] = pose(lambda b: MO.selector(-12.0) if b == "selector" else None)
    out["release_pressed"] = pose(lambda b: MO.mag_release(-4.5) if b == "mag_release" else None)
    for dz in MO.RISER:
        out[f"riser@{dz:g}"] = pose(lambda b, dz=dz: MO.riser(dz) if b == "cheek_riser" else None)

    def bip(b, cant, ext, fold=90.0):
        if b == "bipod":
            return MO.cant(cant)
        for s in ("l", "r"):
            if b == f"bipod_leg_{s}":
                return MO.leg(s, fold, cant)
            if b == f"bipod_leg_{s}_ext":
                return MO.leg_ext(s, fold, ext, cant)
        return None
    for cant in (-15.0, 0.0, 15.0):
        out[f"bipod_deployed_ext76_cant{cant:g}"] = pose(lambda b, c=cant: bip(b, c, 76.0))
    out["bipod_deployed_ext0"] = pose(lambda b: bip(b, 0.0, 0.0))
    out["bipod_folded_ext76"] = pose(lambda b: bip(b, 0.0, 76.0, 0.0))
    return out'''

port('smg_uvproj.py', 'sr_uvproj.py')
port('smg_lmpack.py', 'sr_lmpack.py')
port('smg_ud4.py', 'sr_ud4.py', [('from smg_common import SCRATCH  # noqa: E402', 'from sr_surface import SCRATCH  # noqa: E402')])
port('smg_uv.py', 'sr_uv.py', [
    ('from smg_common import ROOT, SCRATCH, BLEND, PARTS_COLL  # noqa: E402',
     'from sr_surface import ROOT, SCRATCH, WBLEND as BLEND, COLL as PARTS_COLL  # noqa: E402'),
    ('''    if name in SS.CYL_X:
        return UC.cyl_frame(np.array([0.0, 0.0, SS.BORE_Z_B]), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    if name in SS.CYL_Z:
        return UC.cyl_frame(np.array([SS.HINGE_AXIS_B[0], SS.HINGE_AXIS_B[1], 0.0]), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
    return UC.box_frame()''', '''    if name in SS.CYL:
        c, w, u0 = SS.CYL[name]
        return UC.cyl_frame(np.array(c, float), w, u0)
    return UC.box_frame()'''),
    (CONFIGS_OLD, CONFIGS_NEW),
    ('    run("magazine_alone", mag, {}, set(mag))', '    if mag:' + chr(10) + '        run("magazine_alone", mag, {}, set(mag))'),
    ('    L.assert_owner("SMG01", "claude")', '    L.assert_owner("SR01", "claude")'),
])
FRAME_OLD = '''    if name in SS.CYL_X:
        return UC.cyl_frame(np.array([0.0, 0.0, SS.BORE_Z_B]), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    if name in SS.CYL_Z:
        return UC.cyl_frame(np.array([SS.HINGE_AXIS_B[0], SS.HINGE_AXIS_B[1], 0.0]), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0))'''
FRAME_NEW = '''    if name in SS.CYL:
        c, w, u0 = SS.CYL[name]
        return UC.cyl_frame(np.array(c, float), w, u0)'''
port('smg_uv1.py', 'sr_uv1.py', [('from smg_common import SCRATCH, BLEND, PARTS_COLL  # noqa: E402',
                                  'from sr_surface import SCRATCH, WBLEND as BLEND, COLL as PARTS_COLL  # noqa: E402'),
                                 (FRAME_OLD, FRAME_NEW)])
port('smg_bake.py', 'sr_bake.py', [('from smg_common import SCRATCH, GRIP, PARTS_COLL  # noqa: E402',
                                    'from sr_surface import SCRATCH, GRIP, COLL as PARTS_COLL  # noqa: E402')])
port('smg_w2_blender.py', 'sr_w2_blender.py', [
    ('from smg_common import ROOT, SCRATCH, PARTS_COLL  # noqa: E402',
     'from sr_surface import ROOT, SCRATCH, COLL as PARTS_COLL  # noqa: E402'),
    ('TEX = Path(arg("--tex", str(ROOT / "Exports" / "Guns" / "SMG01" / "Textures")))',
     'TEX = Path(arg("--tex", str(SS.TEX)))'),
    ('    order = ["Metal", "Furniture", "Mag"]\n    mats = [GM.game_material(SS.SETS[st]["slot"], f"T_SMG01_{st}", TEX) for st in order]',
     '    order = list(SS.SETS)\n    mats = [GM.game_material(SS.SETS[st]["slot"], f"{SS.STEM}_{st}", TEX) for st in order]'),
    ('    tw = GM.join_copies(parts, "SM_SMG01", coll, slot_of, mats, tile)\n    q0 = qa_check([tw], budget_tris=55000,',
     '    tw = GM.join_copies(parts, "SM_SR01" if SS.TARGET == "gun" else "SM_Att_Scope_LongRange", coll, slot_of, mats, tile)\n'
     '    budget = 55000 if SS.TARGET == "gun" else 8000\n    q0 = qa_check([tw], budget_tris=budget,'),
    ('    q = qa_check([tw], budget_tris=55000,', '    q = qa_check([tw], budget_tris=budget,'),
])
