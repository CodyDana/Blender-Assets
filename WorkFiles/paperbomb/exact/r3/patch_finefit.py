p = r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/paperbomb_finefit.py"
s = open(p, encoding="utf-8").read()
s = s.replace('FINEFIT_VERSION = "1.2.0"', 'FINEFIT_VERSION = "1.3.0"')
old = '''    {"name": "seal_spark_TL", "group": "seal_big", "layer": "red", "kind": "star",
     "centre_mm": (9.6, 126.9), "half_mm": 2.4, "rays": 4},'''
new = '''    # the top-left sparkle is laid SOFT: in the reference it is a soft glint (its rays
    # are a fraction of a pixel wide and read as faint streaks); fitted crisp it came out
    # a hard needle.  ``soft_px``: its erase is blurred by this (source px), in the fit
    # and in the texture alike, so the fit accounts for the softness
    {"name": "seal_spark_TL", "group": "seal_big", "layer": "red", "kind": "star",
     "centre_mm": (9.6, 126.9), "half_mm": 2.4, "rays": 4, "soft_px": 0.45},'''
assert old in s; s = s.replace(old, new)
old = r'''    def render(self, erase_px):
        e = T.fill_polys([q - self.off for q in erase_px], self.h, self.w, ss=16) \
            if erase_px else np.zeros((self.h, self.w))
        cov'''
new = r'''    #: a knock-out laid SOFT (``soft_px``): its erase is blurred by this (source px)
    soft = 0.0

    def render(self, erase_px):
        e = T.fill_polys([q - self.off for q in erase_px], self.h, self.w, ss=16) \
            if erase_px else np.zeros((self.h, self.w))
        if self.soft > 0.0 and erase_px:
            e = T.gauss_blur(np.asarray(e, np.float64), self.soft)
        cov'''
assert old in s, "render"; s = s.replace(old, new)
old = '''        win = _Window(base_polys_px, obs, dens, x0, y0, x1, y1)
        rays = spec["rays"]'''
new = '''        win = _Window(base_polys_px, obs, dens, x0, y0, x1, y1)
        win.soft = float(spec.get("soft_px", 0.0))
        rays = spec["rays"]'''
assert old in s; s = s.replace(old, new)
old = '''            "loss_fit": round(lbest, 5), "polys_px": polys,'''
new = '''            "loss_fit": round(lbest, 5), "polys_px": polys,
            "soft_px": float(spec.get("soft_px", 0.0)),'''
assert old in s; s = s.replace(old, new)
chunk = open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/r3/spike_chunk.py", encoding="utf-8").read()
s = s.rstrip("\n") + "\n" + chunk
old = '''They are stored with the traced group (``knockouts_mm``) and the traced holes they
replace are dropped from the group, so the one JSON carries everything.
"""'''
new = '''They are stored with the traced group (``knockouts_mm``) and the traced holes they
replace are dropped from the group, so the one JSON carries everything.

The same analysis by synthesis re-draws the ENDS of the corner claws' thin prongs as
tapered spikes (``SPIKES``, ``fit_spike``): an erase of the traced tip plus an ink
outline laid in its place (stored as ``spikes_mm`` with the frame).
"""'''
assert old in s; s = s.replace(old, new)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
