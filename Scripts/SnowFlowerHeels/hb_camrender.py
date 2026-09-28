"""Blender camera matching hb_camera.Cam (reference canvas 1254 x 1254) and a Workbench compare render.

    blender -b --factory-startup --python Scripts/SnowFlowerHeels/hb_camrender.py -- <tag> [npz ...]

Writes r1/preview/<tag>_cam.png (render, transparent) and <tag>_cmp.png (reference | render | 50 % overlay).
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hb_camera as HC  # noqa: E402
import hb_common as C  # noqa: E402


def load_cam(path=None):
    p = Path(path) if path else C.CACHE / "camera.json"
    d = json.loads(p.read_text())
    return HC.Cam(d["az"], d["el"], d["s"], d["tx"], d["ty"], d.get("roll", 0.0))


def setup_camera(cam: HC.Cam, matrix_local_to_world=None, size=1254, name="REFCAM"):
    """Orthographic Blender camera reproducing ``cam`` for points given in the local frame. If
    ``matrix_local_to_world`` (4x4 numpy, local mm -> world m) is given, the camera is placed in world space."""
    sc = bpy.context.scene
    cdir, right, up = cam.basis()
    c = size / 2.0
    p0 = ((c - cam.tx) / cam.s) * right + (-(c - cam.ty) / cam.s) * up
    loc = p0 + cdir * 1500.0
    rot = np.column_stack([right, up, cdir])
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = loc
    scale_mm = size / cam.s
    if matrix_local_to_world is not None:
        L = np.asarray(matrix_local_to_world)
        m = L @ m
        # remove the mm->m scale (and any mirror) from the rotation part, keep a proper rotation
        R = m[:3, :3]
        sx = np.linalg.norm(R, axis=0)
        R = R / sx
        if np.linalg.det(R) < 0:
            R[:, 0] = -R[:, 0]
        m[:3, :3] = R
        scale_mm = scale_mm * sx[0]
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, bpy.data.cameras.new(name))
        sc.collection.objects.link(ob)
    ob.data.type = "ORTHO"
    ob.data.ortho_scale = scale_mm
    ob.data.clip_start = 0.001 if matrix_local_to_world is not None else 1.0
    ob.data.clip_end = 10.0 if matrix_local_to_world is not None else 5000.0
    ob.matrix_world = Matrix(m.tolist())
    sc.camera = ob
    sc.render.resolution_x = size
    sc.render.resolution_y = size
    sc.render.resolution_percentage = 100
    return ob


def composite(render_png: Path, out_png: Path):
    import metro_png as png
    ref = png.read(str(C.REF_PNG)).astype(float)
    ref = ref / 255.0 if ref.max() > 1.5 else ref
    ren = png.read(str(render_png)).astype(float)
    ren = ren / 255.0 if ren.max() > 1.5 else ren
    if ren.shape[2] == 4:
        a = ren[..., 3:4]
        ren = ren[..., :3] * a + (1 - a)
    ref = ref[..., :3]
    box = (0, 0, 900, 1210)
    x0, y0, x1, y1 = box
    over = ref * 0.5 + ren * 0.5
    sheet = np.concatenate([ref[y0:y1, x0:x1], ren[y0:y1, x0:x1], over[y0:y1, x0:x1]], axis=1)
    png.write(str(out_png), (np.clip(sheet, 0, 1) * 255).astype(np.uint8))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    tag = argv[0]
    files = argv[1:]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    palette = {"upper": (0.12, 0.12, 0.13, 1), "sole": (0.05, 0.05, 0.05, 1), "insole": (0.3, 0.3, 0.3, 1),
               "stil": (0.1, 0.1, 0.1, 1), "silver_recess": (0.3, 0.28, 0.27, 1), "silver": (0.75, 0.72, 0.7, 1),
               "pearl": (0.95, 0.93, 0.9, 1), "patent": (0.01, 0.01, 0.01, 1), "cap": (0.02, 0.02, 0.02, 1),
               "strap": (0.1, 0.1, 0.1, 1), "leather": (0.09, 0.09, 0.095, 1), "lining": (0.05, 0.05, 0.05, 1),
               "binding": (0.12, 0.12, 0.12, 1), "crackle": (0.18, 0.17, 0.17, 1)}
    for f in files:
        z = np.load(f)
        for n in sorted({k[:-2] for k in z.files if k.endswith("_v")}):
            faces = []
            for suf in ("_f", "_q", "_t"):
                if n + suf in z.files and len(z[n + suf]):
                    faces += z[n + suf].tolist()
            if not faces:
                continue
            me = bpy.data.meshes.new(n)
            me.from_pydata([tuple(map(float, p)) for p in z[n + "_v"]], [], [tuple(map(int, q)) for q in faces])
            me.update()
            for p in me.polygons:
                p.use_smooth = True
            ob = bpy.data.objects.new(n, me)
            sc.collection.objects.link(ob)
            key = n if n in palette else next((k for k in palette if n.startswith(k)), None)
            ob.color = palette.get(key, (0.4, 0.4, 0.45, 1))
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "OBJECT"
    sh.show_cavity = True
    sh.show_backface_culling = False
    sc.render.film_transparent = True
    setup_camera(load_cam())
    out = C.R1 / "preview"
    out.mkdir(parents=True, exist_ok=True)
    rp = out / f"{tag}_cam.png"
    sc.render.filepath = str(rp)
    bpy.ops.render.render(write_still=True)
    composite(rp, out / f"{tag}_cmp.png")
    print("CAMRENDER_OK", out / f"{tag}_cmp.png")


if __name__ == "__main__":
    main()
