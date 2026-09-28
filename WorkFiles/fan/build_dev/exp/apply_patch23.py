p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_gallery.py"
s = open(p, encoding="utf-8").read()
old = s[s.index("def tassel_flat_lay("):s.index("def reference_views(")]
new = '''#: fan2's tassel (RS 8, measured on the photo's silhouette): the cord runs from the rivet to the knot at image
#: angle -150 deg, the skirt lies out at -161.5 deg (RS 8's -159.7 is the whole tassel's line)
TASSEL_CORD_DEG = -150.0
TASSEL_SKIRT_DEG = -161.5


def tassel_flat_lay(spec, fs_arm, tarm, cord_deg: float = TASSEL_CORD_DEG, skirt_deg: float = TASSEL_SKIRT_DEG):
    """SK_Fan_Tassel at the Tassel socket lying out behind the fan in its plane as fan2 shows it (a flat lay,
    not a hang): returns (the tassel armature's world matrix, a pose that bends the skirt at the knot)."""
    from . import fan_tassel as TS
    zt = 0.5 * spec.stack_mm + spec.rivet_proud

    def frame(image_deg):
        th = (image_deg - RV.ROLL_TO_DEG) * D2R          # image angle -> build-frame angle (the tilt is ~0.1 deg)
        d = Vector((math.cos(th), math.sin(th), 0.0))
        zc = -d                                           # tassel -Z (its hang) -> d
        yc = Vector((0.0, 0.0, -1.0))                     # tassel +Y -> behind the fan
        xc = yc.cross(zc)
        return Matrix((xc, yc, zc)).transposed()
    R0 = frame(cord_deg)
    M = R0.to_4x4()
    # the round skirt (up to 8 mm radius) lies behind the fan's back face
    M.translation = Vector((0.0, 0.0, -zt - 0.6 - 8.5)) * 0.001
    # the skirt turned in the plane about the knot's bottom: in tassel space, R0^-1 R1
    R1 = frame(skirt_deg)
    Rl = np.array(R0.transposed() @ R1)
    st = TS.stations(spec)
    p = np.array([0.0, 0.0, st["neck_bot"]])
    T = np.eye(4)
    T[:3, :3] = Rl
    T[:3, 3] = p - Rl @ p
    pose = {"skirt_01": T, "skirt_02": T}
    return fs_arm.matrix_world @ M, pose


'''
s = s.replace(old, new)
old = '''    tarm.matrix_world = tassel_flat_lay(spec, arm, tarm)
    LK.pose(tarm, {})'''
assert old in s
s = s.replace(old, '''    Mt, tpose = tassel_flat_lay(spec, arm, tarm)
    tarm.matrix_world = Mt
    LK.pose(tarm, tpose)''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
