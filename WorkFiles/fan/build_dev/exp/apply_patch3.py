p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/fan_fold.py"
s = open(p, encoding="utf-8").read()
old = '''    def sticks_T(self, s: float) -> List[np.ndarray]:'''
new = '''    def page_tilt_deg(self, s: float = 0.0) -> float:
        """How far the closed pleats lean out of the fan plane: the angle of gap 0's mid-gap fold (outer
        and inner point) above the horizontal, seen from its two leaf lines' midpoint."""
        g = self.solve(s)
        worst = 0.0
        for k in range(2):
            m = apply(g.TA, self.A_mid[k:k + 1])[0]
            a = apply(self.line_T(0, s), self.A_rib[k:k + 1])[0]
            b = apply(self.line_T(1, s), self.B_rib[k:k + 1])[0]
            c = 0.5 * (a + b)
            v = m - c
            worst = max(worst, abs(math.degrees(math.atan2(v[2], math.hypot(v[0], v[1]) if False else
                                                          np.linalg.norm(v[:2] - (v[:2] @ (a[:2] / np.linalg.norm(a[:2])))
                                                                         * (a[:2] / np.linalg.norm(a[:2])))))))
        return worst

    def sticks_T(self, s: float) -> List[np.ndarray]:'''
assert old in s
s = s.replace(old, new, 1)
old2 = '''        for s in samples:
            g = fs.solve(s)
            worst = max(worst, g.crack_mm["valley_mm"], g.crack_mm["mountain_mm"])
        return worst'''
new2 = '''        for s in samples:
            g = fs.solve(s)
            worst = max(worst, g.crack_mm["valley_mm"], g.crack_mm["mountain_mm"])
        # the closed leaf must be a flat stack of pages: penalise any lean past 6 deg
        return worst + 0.01 * max(0.0, fs.page_tilt_deg(0.0) - 6.0)'''
assert old2 in s
s = s.replace(old2, new2)
open(p, "w", encoding="utf-8").write(s)
print("patched")
