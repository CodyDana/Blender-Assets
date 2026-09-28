p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_spec.py"
s = open(p, encoding="utf-8").read()
old = s[s.index("    @property\n    def leaf_z0(self) -> float:"):s.index("    def leaf_line_z(self, i: int) -> float:")]
new = '''    @property
    def leaf_z_pitch(self) -> float:
        """the leaf lines step down one rib pitch per stick"""
        return self.stack_pitch_mm

    @property
    def leaf_z0(self) -> float:
        """The leaf lies ON its ribs: leaf line i (1..24) is ``leaf_on_rib_mm`` above rib i's top face (the ribs are
        glued behind the silk, RS 7), and the 25 steps are all one pitch.  So the front guard's leaf line is one
        pitch above rib 1's (inside the guard's thickness band, beside its inner edge), and the rear guard's is
        just above the rear guard's top face, where the glued flap lies."""
        return self.stick_z(1)[1] + self.leaf_on_rib_mm + self.leaf_z_pitch

    @property
    def leaf_z25(self) -> float:
        return self.leaf_z0 - (self.n_sticks - 1) * self.leaf_z_pitch

'''
s = s.replace(old, new)
s = s.replace('''    leaf_gap_under_guard_mm: float = 0.05''', '''    leaf_on_rib_mm: float = 0.01
    #: the leaf lines' own pitch beyond the rib ends: a rib's top also carries a short slip (its -y half, to
    #: 0.8 mm past the leaf's inner edge) that hides the daylight under the raised inner corners of the pleats
    rib_slip_past_leaf_mm: float = 0.8''')
open(p, "w", encoding="utf-8").write(s)
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_fold.py"
s = open(p, encoding="utf-8").read()
s = s.replace("spec.leaf_gap_under_guard_mm,", "spec.leaf_on_rib_mm,")
open(p, "w", encoding="utf-8").write(s)
p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_geom.py"
s = open(p, encoding="utf-8").read()
old = '''    for name, a0, a1, z, bone, k_edge, piece in (
            ("front", lam0, -spec.front_flap_past_axis_deg, tpl.z[0], "stick_00", 0, 0),
            ("rear", lam25,'''
assert old in s
s = s.replace(old, '''    # only the REAR flap: the leaf glued over the rear guard (RS 2's leaf corner past its axis).  The front guard's
    # leaf line sits beside its inner edge one rib pitch above rib 1; the leaf's corner under the front guard
    # (RS 2) is never visible from the front and is not built
    for name, a0, a1, z, bone, k_edge, piece in (
            ("rear", lam25,''')
# rib slip: -y half extended past the leaf's inner edge
old = '''    cx = -butt + hw0
    xs = [cx, 0.0, r_end - 1.0]'''
assert old in s
s = s.replace(old, '''    cx = -butt + hw0
    r_slip = spec.r_in + spec.rib_slip_past_leaf_mm if slip else None
    xs = [cx, 0.0, r_end - 1.0]''')
old = '''    # top: an arc r = r_end between the two sides (the shoulders are filleted below)
    yl, yr = minus[-1][1], plus[-1][1]
    a0, a1 = math.asin(max(-0.99, yl / r_end)), math.asin(min(0.99, yr / r_end))
    top = [np.array([r_end * math.cos(t), r_end * math.sin(t)]) for t in np.linspace(a0, a1, plan.top_seg + 2)]
    pts = list(minus)
    k_sh0 = len(pts)
    pts += top
    k_sh1 = len(pts) - 1'''
new = '''    # top: an arc r = r_end between the two sides (the shoulders are filleted below).  With a slip, the -y half
    # runs on under the leaf to r_slip and steps down to r_end 0.3 mm short of the leaf line (the closed pages
    # all lie on the +y side of it, so the slip never meets them)
    yl, yr = minus[-1][1], plus[-1][1]
    pts = list(minus)
    if r_slip is not None:
        pts[-1] = np.array([r_slip - 1.0, yl])
        a0 = math.asin(max(-0.99, yl / r_slip))
        ys = -0.3
        top = [np.array([r_slip * math.cos(t), r_slip * math.sin(t)])
               for t in np.linspace(a0, math.asin(ys / r_slip), plan.top_seg + 2)]
        k_sh0 = len(pts)
        pts += top
        pts.append(np.array([math.sqrt(r_end ** 2 - ys ** 2), ys]))
        a1 = math.asin(min(0.99, yr / r_end))
        top2 = [np.array([r_end * math.cos(t), r_end * math.sin(t)]) for t in np.linspace(math.asin(ys / r_end), a1, plan.top_seg + 2)][1:]
        pts += top2
        k_sh1 = len(pts) - 1
    else:
        a0, a1 = math.asin(max(-0.99, yl / r_end)), math.asin(min(0.99, yr / r_end))
        top = [np.array([r_end * math.cos(t), r_end * math.sin(t)]) for t in np.linspace(a0, a1, plan.top_seg + 2)]
        k_sh0 = len(pts)
        pts += top
        k_sh1 = len(pts) - 1'''
assert old in s
s = s.replace(old, new)
s = s.replace('''def rib_outline(spec: FanSpec, i: int, plan: LodPlan, widen_minus: Optional[callable] = None,
                widen_plus: Optional[callable] = None) -> np.ndarray:''', '''def rib_outline(spec: FanSpec, i: int, plan: LodPlan, widen_minus: Optional[callable] = None,
                widen_plus: Optional[callable] = None, slip: bool = True) -> np.ndarray:''')
# box LOD: add slip too
old = '''        return np.array([[-butt + 0.3 * hw0, -hw0], [r_end - 0.5, -hw_top - em(r_end - 2.0)],
                         [r_end - 0.5, hw_top + ep(r_end - 2.0)], [-butt + 0.3 * hw0, hw0]])'''
s = s.replace(old, '''        r_s = spec.r_in + spec.rib_slip_past_leaf_mm
        return np.array([[-butt + 0.3 * hw0, -hw0], [r_s - 0.3, -hw_top - em(r_end - 2.0)], [r_s - 0.3, -0.3],
                         [r_end - 0.5, -0.3], [r_end - 0.5, hw_top + ep(r_end - 2.0)], [-butt + 0.3 * hw0, hw0]])''')
open(p, "w", encoding="utf-8").write(s)
print("ok")
