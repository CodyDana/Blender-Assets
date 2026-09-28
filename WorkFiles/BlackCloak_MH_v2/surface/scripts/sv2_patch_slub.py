# one-off source patch for make_fabric_maps.py (round 2 slub model)
p = r'C:/Users/Cody/Desktop/Blender_Projects/Scripts/garments/blackcloak_v2/make_fabric_maps.py'
s = open(p).read()
a = s.index('# slub threads: along the weave axes')
b = s.index('log("neps")')
new = '''# slub: yarn is thick-thin along its length, so slub shows as short dashes along the two weave axes (half warp, half
# weft: isotropic in aggregate), lighter where the yarn is thick, darker where thin; plus a few long thick threads
def draw_threads(field, count, len_mm, width_mm, logamp, dark_frac, jitter_deg):
    for i in range(count):
        cx, cy = rng.uniform(0, N, 2)
        ang = (0.0 if i % 2 == 0 else math.pi / 2) + math.radians(rng.normal(0, jitter_deg))
        L = rng.uniform(*len_mm) / TEX_MM
        wd = rng.uniform(*width_mm) / TEX_MM
        amp = rng.uniform(*logamp) * (-0.8 if rng.uniform() < dark_frac else 1.0)
        wav_a, wav_l, ph = rng.uniform(0.1, 0.5) * wd, rng.uniform(8, 20) / TEX_MM, rng.uniform(0, 6.28)
        tw = rng.uniform(1.0, 1.6) / TEX_MM                 # twist period
        ca, sa = math.cos(ang), math.sin(ang)
        hb = L / 2 + 3 * wd

        def fn(dx, dy, ca=ca, sa=sa, L=L, wd=wd, amp=amp, wav_a=wav_a, wav_l=wav_l, ph=ph, tw=tw):
            s_ = dx * ca + dy * sa
            t = -dx * sa + dy * ca
            u = np.clip(s_ / L + 0.5, 0, 1)
            prof = np.sin(math.pi * u) ** 0.8 * (np.abs(s_) < L / 2)
            wloc = wd * (0.55 + 0.45 * prof)                # thick in the middle, thinning to the thread
            t2 = t - wav_a * np.sin(2 * math.pi * s_ / wav_l + ph)
            across = np.exp(-(t2 / (0.5 * wloc)) ** 2)
            twist = 0.8 + 0.2 * np.cos(2 * math.pi * (s_ + 0.6 * t2) / tw)
            return amp * prof * across * twist
        stamp(field, cx, cy, abs(ca) * hb + abs(sa) * 3 * wd + 2, abs(sa) * hb + abs(ca) * 3 * wd + 2, fn)


log("slub dashes + threads")
slub = np.zeros((N, N))
draw_threads(slub, P["dash_count"], P["dash_len_mm"], P["dash_width_mm"], P["dash_logamp"], P["dash_dark_frac"],
             P["slub_axis_jitter_deg"])
draw_threads(slub, P["slub_threads"], P["slub_len_mm"], P["slub_width_mm"], P["slub_logamp"], 0.0,
             P["slub_axis_jitter_deg"])

'''
s = s[:a] + new + s[b:]
old = '''    "slub_threads": 90, "slub_len_mm": [12, 55], "slub_width_mm": [0.55, 1.35], "slub_logamp": [0.18, 0.42],'''
assert old in s
s = s.replace(old, '''    "dash_count": 5200, "dash_len_mm": [4, 22], "dash_width_mm": [0.4, 0.95], "dash_logamp": [0.10, 0.30],
    "dash_dark_frac": 0.35,
    "slub_threads": 26, "slub_len_mm": [30, 65], "slub_width_mm": [1.0, 1.7], "slub_logamp": [0.20, 0.38],''')
open(p, 'w').write(s)
print("patched")
