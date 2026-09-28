"""Finalise patch 3: lod_pop also measures the render noise floor (the same LOD rendered with another seed)."""
from pathlib import Path

p = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/flashbang_gallery.py")
s = p.read_text(encoding="utf-8")
a = '''            if k == 0 and turn == turns[0]:
                LK.save_png(out_dir / f"lodpop_diff_d{k}_turn{int(turn)}.png",
                            np.repeat((np.abs(ca - cb).max(2) * 4)[..., None], 3, 2))'''
b = '''            if turn == turns[0]:
                # the noise floor: the SAME LOD (the nearer one) rendered with another sampling seed
                o = pair[0]
                saved = _hide_all_but([o])
                rig = LK.Rig()
                m0 = o.matrix_world.copy()
                sc = bpy.context.scene
                try:
                    R = Matrix.Rotation(math.radians(turn), 4, "Z")
                    o.matrix_world = R
                    tgt = tuple(R @ tgt0)
                    LK.setup_cycles(samples, res=res)
                    sc.cycles.seed = 8
                    LK.studio(rig, floor=False)
                    _fov_camera(rig, _polar(-90.0, 12.0, d * 1000.0, tgt), tgt, res)
                    c = _render_rgba(out_dir / f"lodpop_d{k}_turn{int(turn)}_{o.name}_seed8.png")
                finally:
                    rig.teardown()
                    o.matrix_world = m0
                    _restore(saved)
                cc = c[..., :3] + (1 - c[..., 3:4]) * grey
                nf = float(((np.abs(ca - cc).max(2) > 20 / 255) & obj).sum() / max(obj.sum(), 1))
                rep.setdefault("noise_floor", []).append({"switch": k + 1, "turn": turn, "frac_gt20_same_lod_other_seed":
                                                          round(nf, 5)})
                LK.save_png(out_dir / f"lodpop_diff_d{k}_turn{int(turn)}.png",
                            np.repeat((np.abs(ca - cb).max(2) * 4)[..., None], 3, 2))'''
assert a in s
s = s.replace(a, b)
p.write_text(s, encoding="utf-8")
print("gallery patched (noise floor)")
