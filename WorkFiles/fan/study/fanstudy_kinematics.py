"""FAN_STUDY section 5 arithmetic: rigid single-apex pleat kinematics vs linear-blend skinning.
Run: blender -b --factory-startup --python fanstudy_kinematics.py   (numpy only)."""
import numpy as np, json, math
N = 26                 # sticks incl. guards (fan2 estimate)
G = N - 1              # rib gaps
THETA = math.radians(166.0)   # fan2 opening, image-space measurement
R_TIP, R_OUT, R_IN = 190.0, 184.0, 87.0   # mm from rivet (ESTIMATES)
T_IN = 0.45            # inner stick thickness at the head, mm
out = {"inputs": dict(N=N, theta_deg=166.0, R_tip=R_TIP, r_out=R_OUT, r_in=R_IN, t_inner=T_IN)}
def crease_dir(alpha, beta):
    """free crease unit vector for ribs at +-alpha/2 about +X in the XY plane, panel angle beta (single apex)."""
    c = math.cos(beta) / math.cos(alpha / 2)
    c = min(1.0, c); g = math.acos(c)
    return np.array([math.cos(g), 0.0, -math.sin(g)]), g
rows = []
for ratio in (1.10, 1.20, 1.30):
    PSI = ratio * THETA; beta = PSI / (2 * G); a_open = THETA / G
    v_open, g_open = crease_dir(a_open, beta)
    # isometry check over the whole range: arm (rib point -> crease point at same radius) length vs developed chord
    errs = []
    for f in np.linspace(0, 1, 201):
        a = a_open * f
        v, g = crease_dir(a, beta)
        u = np.array([math.cos(a/2), math.sin(a/2), 0.0])
        errs.append(abs(np.linalg.norm(R_OUT*u - R_OUT*v) - 2*R_OUT*math.sin(beta/2)))
    # linear blend skinning, bind = open pose, crease vertex 50/50 on the two rib bones
    lbs = []
    for f in np.linspace(0, 1, 201):
        a = a_open * f; d = (a_open - a) / 2        # each rib rotates by d toward the mid line
        p = R_OUT * v_open
        def rz(t, q): return np.array([q[0]*math.cos(t)-q[1]*math.sin(t), q[0]*math.sin(t)+q[1]*math.cos(t), q[2]])
        # rib i sits at -a_open/2 in bind, moves to -a/2: rotation +d; rib i+1 rotation -d
        pl = 0.5 * (rz(+d, p) + rz(-d, p))
        u = np.array([math.cos(a/2), math.sin(a/2), 0.0]) * R_OUT
        arm = np.linalg.norm(u - pl); true = 2*R_OUT*math.sin(beta/2)
        true_v, _ = crease_dir(a, beta)
        lbs.append(dict(open_frac=round(float(f),3), arm_err_pct=round(100*(arm-true)/true,2),
                        crease_pos_err_mm=round(float(np.linalg.norm(pl - R_OUT*true_v)),2)))
    worst = max(lbs, key=lambda d: abs(d["arm_err_pct"]))
    rows.append(dict(psi_over_theta=ratio, psi_deg=round(math.degrees(PSI),1), beta_deg=round(math.degrees(beta),3),
        alpha_open_deg=round(math.degrees(a_open),3), gamma_open_deg=round(math.degrees(g_open),3),
        pleat_depth_open_rim_mm=round(R_OUT*math.sin(g_open),2), pleat_depth_open_leafbase_mm=round(R_IN*math.sin(g_open),2),
        closed_fin_depth_rim_mm=round(R_OUT*math.sin(beta),2), page_width_rim_mm=round(2*R_OUT*math.sin(beta/2),2),
        rigid_model_max_arm_error_mm=float(max(errs)),
        lbs_closed=lbs[0], lbs_worst=worst, lbs_half=lbs[100]))
out["pleat_table"] = rows
# stacking: rigid sticks stacked by t at the rivet; regime switch when r*alpha ~ t
out["stack"] = dict(inner_stack_mm=round(24*T_IN,2), with_guards_2mm=round(24*T_IN+4,2),
    switch_alpha_deg_at_rim=round(math.degrees(T_IN/R_OUT),4), switch_total_opening_deg=round(G*math.degrees(T_IN/R_OUT),2))
# slip overlap: adjacent slips of width w at radius r overlap when alpha < w/r
for w in (3.0, 5.0):
    out[f"slip_overlap_w{int(w)}"] = dict(total_opening_below_deg=round(G*math.degrees(w/R_OUT),1))
# derived opening angles from sourced closed length / open width pairs (pivot 20 mm above the butt, ESTIMATE)
pairs = {"21cm/38cm silk (healing-sounds)": (210, 380), "21cm/36.1cm paper (BECOS 20 g)": (210, 361),
         "22.5cm/41.5cm (BECOS 35 g)": (225, 415), "20.3cm/34.3cm (Wrapables)": (203, 343), "21.2cm/39cm (getmyfan)": (212, 390)}
out["derived_opening"] = {}
for k,(L,W) in pairs.items():
    R = L - 20.0; s = W / (2*R)
    out["derived_opening"][k] = ">=180 (width >= 2R)" if s >= 1 else round(2*math.degrees(math.asin(s)),1)
# mass estimate
rho_bamboo = 0.70e-3   # g/mm^3 (Moso 0.65-0.71 g/cm3)
inner = 24 * ((6.0*T_IN*(R_IN+20)) + (R_OUT-R_IN)*3.0*0.25)      # gorge slat + leaf slip
guards = 2 * (R_TIP+20) * 8.0 * 2.0
leaf_area = 0.5 * (1.20*THETA) * (R_OUT**2 - R_IN**2)
m = dict(inner_mm3=round(inner), guards_mm3=round(guards), bamboo_g=round((inner+guards)*rho_bamboo,2),
         leaf_area_mm2=round(leaf_area), silk_g_at_35gsm=round(leaf_area*35e-6,2), silk_g_at_52gsm=round(leaf_area*52e-6,2))
m["total_without_tassel_g"] = round(m["bamboo_g"] + m["silk_g_at_52gsm"] + 0.5, 1)
out["mass"] = m
print(json.dumps(out, indent=1))
json.dump(out, open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/study/fanstudy_kinematics.json","w"), indent=1)
