"""SHEATH_STUDY.md section 4 arithmetic. System Python, stdlib only.

Inputs are measured, not assumed:
  B: revision-3 SF_Blade sections (sword frame, mm; Z along the blade from the grip centre,
     X across, -X = edge side, +X = spine side), from measure_r3_blade_profile.py on
     Assets/SnowFlower/SnowFlower_Master.blend (read only).
  S: sheath reference silhouette rows (px, 1024x1536 image, row 0 = top), from
     measure_sheath_reference_rows.py (luminance < 0.85 mask).
Mouth rim = image row 47, placed at sword Z = 171.5 (0.7 mm under the guard pendant, Z 170.8).
k = mm per reference pixel. c = sheath axis position in sword X. margin = shell + clearance per side.
"""
import math
B=[(142,-23.0,23.0),(190,-22.9,22.9),(270,-22.7,22.8),(380,-22.4,22.7),(500,-22.2,22.5),(620,-21.9,22.4),(730,-21.6,22.2),(800,-21.4,22.2),(860,-19.3,23.2),(920,-13.2,25.3),(975,-3.3,27.4),(1020,8.1,29.0),(1051,17.9,29.9),(1071,25.0,30.3),(1081,28.9,30.5),(1085,30.5,30.5)]
S=[(45,450,560),(51,450,560),(71,449,564),(91,432,576),(111,440,569),(131,448,562),(151,455,556),(171,458,554),(271,458,554),(291,454,557),(311,452,560),(331,459,554),(391,460,552),(491,460,551),(591,461,550),(691,462,549),(791,463,547),(891,464,546),(991,465,544),(1091,467,543),(1191,468,541),(1291,469,539),(1311,466,543),(1331,467,542),(1351,465,544),(1371,466,543),(1391,471,538),(1411,474,535),(1431,478,531),(1451,483,525),(1471,490,518),(1491,500,508),(1497,504,504)]
AX=505.5; YM=47; ZM=171.5
def interp(t,y,i):
    for a,b in zip(t,t[1:]):
        if a[0]<=y<=b[0]:
            u=(y-a[0])/(b[0]-a[0]); return a[i]+(b[i]-a[i])*u
    return None
def half(y):
    l=interp(S,y,1); r=interp(S,y,2)
    return None if l is None else min(AX-l,r-AX)
def need(z,c,m): return max(interp(B,z,2)-c,c-interp(B,z,1))+m
def excess(k,c,m): return max(need(z,c,m)-half(YM+(z-ZM)/k)*k for z in range(172,1086))
out=[]
out.append("A. Fixed offset, reference outline kept: worst slack (negative = blade pokes out)")
for m in (2.0,3.0,4.0):
    for k in (0.66,0.68,0.70,0.72,0.75,0.80,0.85):
        c,e=min(((c10/10,excess(k,c10/10,m)) for c10 in range(-50,151)),key=lambda t:t[1])
        out.append(" margin %.1f k %.2f  best c %+.1f  slack %+.1f mm  mouth->point %.0f mm"%(m,k,c,-e,(1497-YM)*k))
out.append("B. k=0.70, fixed offset, widen body where needed")
for m in (2.0,3.0):
    c,e=min(((c10/10,excess(0.70,c10/10,m)) for c10 in range(0,151)),key=lambda t:t[1])
    out.append(" margin %.1f  c %+.1f  widening per side %.1f mm"%(m,c,e))
    for z in (172,300,500,600,700,800,860,920,975,1020,1051,1085):
        y=YM+(z-ZM)/0.70
        out.append("   Z %4d  ref row %4.0f  ref width %.1f  needed %.1f"%(z,y,2*half(y)*0.70,2*need(z,c,m)))
out.append("C. Draw path: spine sweep +30.5 passes the whole body -> body full width >= 2*(30.5-c+m)")
for m in (2.0,3.0): out.append(" margin %.1f c 6.2 -> %.1f mm"%(m,2*(30.5-6.2+m)))
open(__file__.replace('.py','.txt'),'w').write("\n".join(out)+"\n"); print("\n".join(out))
