"""SR01 W3 look check from the EXPORTED bytes (fresh Blender process, Workbench; the SMG's smg_rig_render.py, adapted):

    blender -b --factory-startup --python Scripts/guns/sniper/sr_rig_render.py

SK_SR01.fbx + every clip FBX re-imported, SM_SR01_Mag.fbx (LOD0) carried on the 'magazine' bone at the Mag socket (zero
relative transform), SM_Att_Scope_LongRange.fbx (LOD0) on Rail_Top + 2 slots; rendered at every clip's key frames
(Fire, BoltCycle, Reload, ReloadEmpty, Selector, BipodDeploy, BipodStow from the side AND the front (the 12 deg splay),
CheekRiser). Then SM_SR01.fbx: LOD0-3 side by side (same scale) and each LOD at a size matching its switch distance.
Frames + review/w3/rig/rig_contact_sheet.png, review/w3/rig/lod_switch_sheet.png (copies in Renders/Guns/SR01/).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import ROOT, WORK, RENDERS, GRIP, D  # noqa: E402

if "--sheets" not in sys.argv:
    import bpy  # noqa: E402
    from mathutils import Matrix, Vector  # noqa: E402

EXP = ROOT / "Exports" / "Guns" / "SR01"
OUT = WORK / "review" / "w3" / "rig"
OUT.mkdir(parents=True, exist_ok=True)
CLIPS = ("A_SR01_Fire", "A_SR01_BoltCycle", "A_SR01_Reload", "A_SR01_ReloadEmpty", "A_SR01_Selector",
         "A_SR01_BipodDeploy", "A_SR01_BipodStow", "A_SR01_CheekRiser")


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def import_fbx(p):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(p), use_custom_normals=True, automatic_bone_orientation=False)
    return [o for o in bpy.data.objects if o not in before]


def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
    sc.world = bpy.data.worlds.new("w") if sc.world is None else sc.world
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.clip_end = 100.0
    return sc, cam


def look(cam, eye, target, scale):
    cam.location = Vector(eye)
    d = Vector(target) - Vector(eye)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = scale


def sheet(paths, out, cols=4, w=560, h=400, title=None):
    from PIL import Image, ImageDraw
    ims = [Image.open(x).convert("RGB").resize((w, h)) for x in paths]
    rows = (len(ims) + cols - 1) // cols
    top = 24 if title else 0
    S = Image.new("RGB", (cols * w, rows * (h + 20) + top), (255, 255, 255))
    if title:
        ImageDraw.Draw(S).text((6, 4), title, fill=(0, 0, 0))
    for i, (im, x) in enumerate(zip(ims, paths)):
        r_, c_ = divmod(i, cols)
        S.paste(im, (c_ * w, top + r_ * (h + 20) + 20))
        ImageDraw.Draw(S).text((c_ * w + 6, top + r_ * (h + 20) + 4), Path(x).stem, fill=(0, 0, 0))
    S.save(out)


def main():
    clear()
    sk = import_fbx(EXP / "SK_SR01.fbx")
    arm = next(o for o in sk if o.type == "ARMATURE")
    acts = {}
    for c in CLIPS:
        objs = import_fbx(EXP / f"{c}.fbx")
        a2 = next(o for o in objs if o.type == "ARMATURE")
        act = a2.animation_data.action
        act.name = c
        act.use_fake_user = True
        acts[c] = a2                         # the clip's OWN imported armature drives the SK mesh (no re-targeting)
        for o in objs:
            if o is not a2:
                bpy.data.objects.remove(o, do_unlink=True)

    def first_lod(path, stem):
        objs = import_fbx(path)
        keep = None
        for o in objs:
            if o.type == "MESH" and o.name.startswith(f"{stem}_LOD0"):
                keep = o
            elif o.type == "MESH":
                o.hide_render = True
        keep.parent = None
        return keep
    mag0 = first_lod(EXP / "SM_SR01_Mag.fbx", "SM_SR01_Mag")
    scope0 = first_lod(EXP / "SM_Att_Scope_LongRange.fbx", "SM_Att_Scope_LongRange")
    mount_B = (Vector(D["scope_attachment"]["mount_M"]) - Vector(GRIP.tolist())) * 0.001
    scope0.matrix_world = Matrix.Translation(mount_B)
    sc, cam = setup_scene()

    skmesh = next(o for o in sk if o.type == "MESH")
    mod = next(m for m in skmesh.modifiers if m.type == "ARMATURE")
    drv = {"arm": arm}

    def place_mag():
        a = drv["arm"]
        pb = a.pose.bones["magazine"]
        M = a.matrix_world @ pb.matrix
        loc, rot, _s = M.decompose()
        mag0.matrix_world = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()

    R = lambda x, z: ((x, -2.0, z), (x, 0.0, z))                 # noqa: E731  from the right (-Y)
    F_ = ((3.0, 0.0, -0.02), (0.5, 0.0, -0.02))                    # from the front (+X): the splay
    Q = ((0.95, -0.85, 0.45), (0.45, 0.0, -0.03))                  # front-right 3/4
    shots = [
        ("fire_f02_trigger_pulled", "A_SR01_Fire", 2, *R(0.07, 0.0), 0.22),
        ("bolt_f06_unlocked_q34", "A_SR01_BoltCycle", 6, (0.45, -0.6, 0.45), (0.12, 0.0, 0.08), 0.42),
        ("bolt_f14_back", "A_SR01_BoltCycle", 14, *R(0.12, 0.06), 0.5),
        ("bolt_f14_back_top", "A_SR01_BoltCycle", 14, (0.12, -0.02, 2.0), (0.12, -0.02, 0.0), 0.5),
        ("reload_f03_paddle_pressed", "A_SR01_Reload", 3, *R(0.15, 0.0), 0.35),
        ("reload_f10_insertstart", "A_SR01_Reload", 10, *R(0.15, -0.03), 0.45),
        ("reload_f18_dropped", "A_SR01_Reload", 18, *R(0.15, -0.08), 0.6),
        ("reload_f47_camming_in", "A_SR01_Reload", 47, *R(0.15, 0.0), 0.35),
        ("reloadempty_f00_bolt_open", "A_SR01_ReloadEmpty", 0, *R(0.15, 0.04), 0.5),
        ("reloadempty_f72_closing", "A_SR01_ReloadEmpty", 72, *R(0.15, 0.04), 0.5),
        ("selector_f10_safe", "A_SR01_Selector", 10, *R(0.065, 0.08), 0.12),
        ("riser_f08_up", "A_SR01_CheekRiser", 8, *R(-0.17, 0.09), 0.3),
        ("riser_f18_down", "A_SR01_CheekRiser", 18, *R(-0.17, 0.09), 0.3),
    ]
    for f in (0, 6, 11, 24, 36):
        shots.append((f"deploy_f{f:02d}_side", "A_SR01_BipodDeploy", f, *R(0.35, -0.05), 1.35))
        shots.append((f"deploy_f{f:02d}_front", "A_SR01_BipodDeploy", f, *F_, 0.55))
    shots.append(("deploy_f36_q34", "A_SR01_BipodDeploy", 36, *Q, 1.3))
    for f in (0, 14, 25, 36):
        shots.append((f"stow_f{f:02d}_side", "A_SR01_BipodStow", f, *R(0.35, -0.05), 1.35))
    written = []
    for name, cname, f, eye, tgt, scale in shots:
        a2 = acts[cname]
        off = int(round(a2.animation_data.action.frame_range[0]))     # the importer starts takes at frame 1
        sc.frame_set(f + off)
        bpy.context.view_layer.update()
        # absolute pose matrices (armature space) copied bone by bone, parents first: a clip FBX whose first frame is
        # not rest (BipodStow, ReloadEmpty) carries that frame as its bind pose, so its local curves cannot be re-used
        for b in arm.data.bones:
            arm.pose.bones[b.name].matrix = a2.pose.bones[b.name].matrix.copy()
            bpy.context.view_layer.update()
        place_mag()
        look(cam, eye, tgt, scale)
        p = OUT / f"{name}.png"
        sc.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        written.append(str(p))
    # ------------------------------------------------------------ LOD switch sheet from SM_SR01.fbx
    clear()
    sc, cam = setup_scene()
    objs = import_fbx(EXP / "SM_SR01.fbx")
    lods = sorted([o for o in objs if o.type == "MESH" and "_LOD" in o.name and not o.name.startswith("UCX_")],
                  key=lambda o: o.name)
    for o in objs:
        if o.name.startswith("UCX_"):
            o.hide_render = True
    sizes = json.loads((WORK / "gates" / "game_lod_sizes.json").read_text())
    r = float(sizes["bounds_radius_m"])
    lod_paths = []
    for k, o in enumerate(lods):
        for o2 in lods:
            o2.hide_render = o2 is not o
        look(cam, (0.25, -2.0, 0.0), (0.25, 0.0, 0.0), 1.25)
        sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
        p = OUT / f"lod{k}_side.png"
        sc.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        lod_paths.append(str(p))
    for k in (1, 2, 3):
        s = sizes["SM_SR01"][k]
        d = 1.778 * r / s
        px = max(8, int(round(2560 * (2 * r) / (2 * d))))           # the gun's screen width at its switch distance
        for kk in (k - 1, k):
            for o2 in lods:
                o2.hide_render = o2 is not lods[kk]
            look(cam, (0.25, -2.0, 0.0), (0.25, 0.0, 0.0), 1.25)
            sc.render.resolution_x, sc.render.resolution_y = px, max(6, int(px * 0.714))
            p = OUT / f"switch_{k - 1}{k}_lod{kk}_{px}px.png"
            sc.render.filepath = str(p)
            bpy.ops.render.render(write_still=True)
            lod_paths.append(str(p))
    (OUT / "frames.json").write_text(json.dumps({"clips": written, "lods": lod_paths}, indent=1))
    print("[SR01-rr] DONE", len(written), len(lod_paths))


def sheets_main():
    """plain Python (PIL): the two contact sheets from frames.json (Blender's Python has no PIL)."""
    fr = json.loads((OUT / "frames.json").read_text())
    sheet(fr["clips"], OUT / "rig_contact_sheet.png", cols=5,
          title="SR01 W3: exported SK_SR01 + clips, SM_SR01_Mag on Mag, scope on Rail_Top + 2 (Workbench)")
    sheet(fr["lods"], OUT / "lod_switch_sheet.png", cols=4,
          title="SM_SR01.fbx LOD0-3 (side, same scale), then each switch pair at its on-screen size (2560 px wide view)")
    for n in ("rig_contact_sheet.png", "lod_switch_sheet.png"):
        shutil.copy(OUT / n, RENDERS / f"w3_{n}")
    print("[SR01-rr] sheets written")


if "--sheets" in sys.argv:
    sheets_main()
else:
    main()
