import json, math, numpy as np
d = json.load(open("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/senban/contour/senban_contour_results.json"))
P = d["primary_threshold"]; S = d["shadow_corrected"]
def ang(u):
    a = math.degrees(math.atan2(u[1], u[0]))
    while a <= -90: a += 180
    while a > 90: a -= 180
    return a
for name, oc, hc in [("P", [[c["x"], c["y"]] for c in P["outer"]["corners"]], P["hole"]["sharp_corners"]),
                     ("S", [[c["x"], c["y"]] for c in S["outer"]["corners"]], S["hole"]["sharp_corners"])]:
    oc = np.array(oc); hc = np.array(hc)
    rel = [ang(hc[(k+1)%4]-hc[k]) - ang(oc[(k+1)%4]-oc[k]) for k in range(4)]
    # distance of each hole corner from the outer diagonal through the matching outer corner
    dd = []
    for k in range(4):
        a = oc[k]; b = oc[(k+2)%4]; u = (b-a)/np.linalg.norm(b-a); n = np.array([-u[1], u[0]])
        dd.append(float((hc[k]-a) @ n))
    Sref = np.mean([np.linalg.norm(oc[(k+1)%4]-oc[k]) for k in range(4)])
    hs = [np.linalg.norm(hc[(k+1)%4]-hc[k]) for k in range(4)]
    # centre offset in plate frame
    cen = np.array(P["outer"]["center"] if name=="P" else S["outer"]["center"])
    hcen = hc.mean(0)
    ux = (oc[1]-oc[0])/np.linalg.norm(oc[1]-oc[0]) + (oc[2]-oc[3])/np.linalg.norm(oc[2]-oc[3]); ux/=np.linalg.norm(ux); uy=np.array([-ux[1],ux[0]])
    off = hcen-cen
    rot = np.mean([ang(oc[1]-oc[0]), ang(oc[2]-oc[3]), ang(oc[2]-oc[1])-90, ang(oc[3]-oc[0])-90])
    print(name, "rel_deg", np.round(rel,2), "mean|rel|", round(float(np.mean(np.abs(rel))),2),
          "hole-corner-to-diag px", np.round(dd,2), "Sref", round(Sref,1), "hole sides", np.round(hs,1),
          "hole mean", round(float(np.mean(hs)),2), "hole/S", round(float(np.mean(hs)/Sref),4),
          "hole sd/S", round(float(np.std(hs)/Sref),4),
          "offset plate px", np.round([off@ux, off@uy],2), "offset/S", np.round([off@ux/Sref, off@uy/Sref],4),
          "plate rotation in image deg", round(float(rot),2))
    # hole width vs height
    print("   hole width(top,bottom) vs height(right,left):", round((hs[0]+hs[2])/2,1), round((hs[1]+hs[3])/2,1),
          " outer width vs height:", round((np.linalg.norm(oc[1]-oc[0])+np.linalg.norm(oc[2]-oc[3]))/2,1),
          round((np.linalg.norm(oc[2]-oc[1])+np.linalg.norm(oc[3]-oc[0]))/2,1))
ps = P["outer"]["sides"]; ss = S["outer"]["sides"]
print("P sag/chord", [round(s["sag_over_chord"],4) for s in ps], "mean", round(np.mean([s["sag_over_chord"] for s in ps]),4), "sd", round(np.std([s["sag_over_chord"] for s in ps]),4))
print("P sag_contour/chord", [round(s["sag_contour_over_chord"],4) for s in ps])
print("P sag px", [round(s["sagitta_circle_px"],2) for s in ps], "mean", round(np.mean([s["sagitta_circle_px"] for s in ps]),2), "/Sref", round(np.mean([s["sagitta_circle_px"] for s in ps])/P["outer"]["S_ref_px"],4))
print("P R/c", [round(s["R_over_chord"],3) for s in ps], "mean", round(np.mean([s["R_over_chord"] for s in ps]),3))
print("S sag/chord", [round(s["sag_over_chord"],4) for s in ss], "mean", round(np.mean([s["sag_over_chord"] for s in ss]),4), "sd", round(np.std([s["sag_over_chord"] for s in ss]),4))
print("S sag px", [round(s["sagitta_px"],2) for s in ss], "mean", round(np.mean([s["sagitta_px"] for s in ss]),2), "/Sref", round(np.mean([s["sagitta_px"] for s in ss])/S["outer"]["S_ref_px"],4))
print("S R/c", [round(s["R_over_chord"],3) for s in ss], "mean", round(np.mean([s["R_over_chord"] for s in ss]),3))
print("P tip", [round(c["angle_circle_tangents_deg"],2) for c in P["outer"]["corners"]], "mean", round(np.mean([c["angle_circle_tangents_deg"] for c in P["outer"]["corners"]]),2))
print("P tip local", [round(c["angle_local_lines_deg"],2) for c in P["outer"]["corners"]], "mean", round(np.mean([c["angle_local_lines_deg"] for c in P["outer"]["corners"]]),2))
print("S tip", [round(c["angle_circle_tangents_deg"],2) for c in S["outer"]["corners"]], "mean", round(np.mean([c["angle_circle_tangents_deg"] for c in S["outer"]["corners"]]),2))
tips = [(c["tip_contour_x"], c["tip_contour_y"]) for c in P["outer"]["corners"]]
print("S corner to contour tip px", [round(math.hypot(c["x"]-t[0], c["y"]-t[1]),1) for c, t in zip(S["outer"]["corners"], tips)])
print("P diag/Sref", [round(x/P["outer"]["S_ref_px"],4) for x in P["outer"]["diag_px"]], "S diag/Sref", [round(x/S["outer"]["S_ref_px"],4) for x in S["outer"]["diag_px"]])
print("P adj sd", round(np.std(P["outer"]["adjacent_px"]),2), "S adj sd", round(np.std(S["outer"]["adjacent_px"]),2))
bev = d["bevel"]; med = [bev[s]["width_median_px"] for s in ["top","right","bottom","left"]]
print("bevel medians", med, "mean", round(np.mean(med),2), "sd", round(np.std(med),2), "/Sref S", round(np.mean(med)/S["outer"]["S_ref_px"],4), "/Sref P", round(np.mean(med)/P["outer"]["S_ref_px"],4))
fl = d["hole_fillet_constrained_fit"]; print("fillets", [(f["corner"], f["r_px"]) for f in fl])
