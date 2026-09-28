"""Reference-traced guard: bowed shoulders, cupped leaves and short thorn lace.

Contour landmarks use the supplied detail view, with image-space +vertical
mapped to blade-local +Z.  Hidden returns are construction inferences.
"""

def sf_guard_contour(outline,sharp=(),steps=5):
    """Closed Hermite contour; retain selected forged corners as true cusps."""
    pts=[Vector((x,z)) for x,z in outline];result=[];n=len(pts)
    for i,b in enumerate(pts):
        a,c,d=pts[(i-1)%n],pts[(i+1)%n],pts[(i+2)%n]
        m0=(c-b) if i in sharp else (c-a)*.5
        m1=(c-b) if (i+1)%n in sharp else (d-b)*.5
        for j in range(steps):
            t=j/steps
            p=(2*t**3-3*t*t+1)*b+(t**3-2*t*t+t)*m0+(-2*t**3+3*t*t)*c+(t**3-t*t)*m1
            result.append((p.x,p.y))
    return result

def sf_guard_plaque(name,outline,side,base,depth,material='BlackenedSteel',ridge=.0012):
    pts=[Vector((x,0,z)) for x,z in outline];cen=sum(pts,Vector())/len(pts);n=len(pts)
    # Concentric surface rings give the forged leaf a continuous crown rather
    # than shading one large triangle fan as if it were a flat badge.
    vs=[(cen.x,side*(base+depth+ridge),cen.z)]
    for fraction,lift in ((.32,.95),(.70,.65),(1.0,0)):
        for p in pts:
            q=cen+(p-cen)*fraction
            vs.append((q.x,side*(base+depth+ridge*lift),q.z))
    vs.extend((p.x,side*base,p.z) for p in pts)
    fs=[]
    for i in range(n):
        j=(i+1)%n;fs.append((0,1+i,1+j))
        for ring in range(3):
            a=1+ring*n;b=1+(ring+1)*n
            fs.append((a+i,b+i,b+j,a+j))
    fs.append(tuple(3*n+1+i for i in reversed(range(n))))
    add(name,material,'02_Guard',vs,fs)

def sf_guard_border(name,outline,side,y,width=.00070,material='Silver'):
    # Squared polished lip, rather than a bright rounded wire.
    pts=[Vector((x,side*y,z)) for x,z in outline];vs=[];fs=[];n=len(pts)
    for i,p in enumerate(pts):
        tangent=(pts[(i+1)%n]-pts[i-1]).normalized();lat=Vector((tangent.z,0,-tangent.x)).normalized()
        for w,d in [(-width/2,-.00018),(width/2,-.00018),(width/2,.00018),(-width/2,.00018)]:vs.append(p+lat*w+Vector((0,side*d,0)))
    for i in range(n):
        j=(i+1)%n
        for k in range(4):fs.append((i*4+k,j*4+k,j*4+(k+1)%4,i*4+(k+1)%4))
    add(name,material,'02_Guard',vs,fs)

# The hidden tang seat joins the existing ferrule to the guard instead of
# leaving the crown ornament suspended across an empty neck.
sf_seat=[(-.014,.108),(.014,.108),(.014,.114),(.011,.121),
         (.009,.128),(-.009,.128),(-.011,.121),(-.014,.114)]
extrude('SF_Guard_CollarSeat',sf_seat,.0250,'Recess','02_Guard')

sf_wing_controls=[
    (.0130,.1220),(.0310,.1208),(.0391,.1189),(.0403,.1140),
    (.0502,.1193),(.0587,.1284),(.0634,.1370),(.0580,.1441),
    (.0502,.1508),(.0409,.1580),(.0374,.1518),(.0380,.1450),
    (.0340,.1377),(.0250,.1320),(.0170,.1260)]
sf_wing=sf_guard_contour(sf_wing_controls,sharp=(0,1,2,3,9),steps=5)
for sf_sign in (-1,1):
    sf_outline=[(sf_sign*x,z) for x,z in sf_wing]
    extrude('SF_Guard_Wings',sf_outline,.009,'Recess','02_Guard')
    for sf_side in (-1,1):
        sf_guard_border('SF_Guard_ShoulderEdge',sf_outline,sf_side,.0053,.0018)
        sf_inset=[(sf_sign*(.041+(x-.041)*.84),.136+(z-.136)*.82) for x,z in sf_wing]
        sf_guard_border('SF_Guard_SteppedRim',sf_inset,sf_side,.0060,.00080,'Inlay')
        # The reference has two bowed ribs with a hooked junction and lower
        # pointed return, not repeated concentric decorative circles.
        for sf_idx,sf_curve2 in enumerate([
            [(.025,.126),(.036,.128),(.047,.132),(.055,.139),(.050,.145)],
            [(.033,.132),(.043,.132),(.048,.137),(.047,.146),(.041,.154)],
            [(.055,.139),(.054,.134),(.048,.133),(.043,.136),(.044,.143)],
            [(.041,.154),(.039,.147),(.038,.141),(.034,.137)]
        ]):
            sf_pts=[(sf_sign*x,sf_side*(.0068+.00035*(sf_idx%2)),z) for x,z in sf_curve2]
            tube('SF_Guard_ShoulderScrolls',smooth_path(sf_pts,7),.00062,'Inlay','02_Guard',7)
            for sf_j in (1,3):
                sf_p=Vector(sf_pts[sf_j]);sf_q=sf_p+Vector((sf_sign*.0018,sf_side*.0001,-.0034))
                tube('SF_Guard_ShoulderThorns',[sf_p,sf_p.lerp(sf_q,.5)+Vector((sf_sign*.001,0,0)),sf_q],lambda t:.00061*(1-.85*t),'Silver','02_Guard',6)

# Broader vertical cups: narrower reach than the previous diagonal leaf fan.
sf_leaf=[(.0081,.1270),(.0193,.1270),(.0291,.1317),(.0348,.1419),
         (.0362,.1600),(.0167,.1547),(.0079,.1485),(.0043,.1416)]
sf_small=[(.005,.123),(.011,.117),(.020,.114),(.028,.113),(.022,.119),(.014,.123)]
for sf_side in (-1,1):
    for sf_sign in (-1,1):
        sf_under=[(sf_sign*x,.129+(z-.129)*1.01+.0025) for x,z in sf_leaf]
        sf_guard_plaque('SF_Guard_UnderLeaves',sf_under,sf_side,.006,.0012,'Recess',.001)
        sf_guard_border('SF_Guard_UnderLeafRims',sf_under,sf_side,.0082,.0011)
        for sf_nm,sf_poly,sf_y in [('UpperLeaf',sf_small,.0090),('MainLeaf',sf_leaf,.0120)]:
            sf_curve=[(sf_sign*x,z) for x,z in sf_guard_contour(sf_poly,sharp=(0,4) if sf_nm=='MainLeaf' else (0,3),steps=6)]
            sf_guard_plaque('SF_Guard_'+sf_nm,sf_curve,sf_side,sf_y,.0014,'BlackenedSteel',.0026)
            sf_lipwidth=.00165 if sf_nm=='MainLeaf' else .0010
            sf_guard_border('SF_Guard_'+sf_nm+'Lip',sf_curve,sf_side,sf_y+.00165,sf_lipwidth)
            # A wide metal lip edged with a fine dark groove, rather than two
            # equally bright wire outlines around the black leaf.
            sf_cx=sf_sign*(.0198 if sf_nm=='MainLeaf' else .016);sf_cz=.1412 if sf_nm=='MainLeaf' else .1185
            sf_inner=[(sf_cx+(x-sf_cx)*.925,sf_cz+(z-sf_cz)*.947) for x,z in sf_curve]
            sf_guard_border('SF_Guard_'+sf_nm+'Inset',sf_inner,sf_side,sf_y+.00195,.00028,'Recess')
    sf_pendant_controls=[(0,.136),(.0087,.139),(.0116,.147),(.0095,.157),
                         (.0055,.164),(0,.170),(-.0055,.164),(-.0095,.157),
                         (-.0116,.147),(-.0087,.139)]
    sf_pendant=sf_guard_contour(sf_pendant_controls,sharp=(0,5),steps=6)
    sf_guard_plaque('SF_Guard_CentralPendant',sf_pendant,sf_side,.006,.0012,'BlackenedSteel',.002)
    sf_guard_border('SF_Guard_PendantOuterLip',sf_pendant,sf_side,.0076,.0016)
    # Compact thorn lace ends well above the exposed tip of the larger leaf.
    sf_inner=[(0,.1382),(.0056,.1394),(.0077,.1425),(.0056,.1475),
              (0,.1524),(-.0056,.1475),(-.0077,.1425),(-.0056,.1394)]
    sf_guard_border('SF_Guard_PendantPiercedFrame',sf_inner,sf_side,.0128,.00095)
    for sf_sign in (-1,1):
        sf_pts=[(0,sf_side*.0133,.1517),(sf_sign*.0017,sf_side*.0135,.1478),
                (sf_sign*.0041,sf_side*.0135,.1465),(sf_sign*.0031,sf_side*.0133,.1434),
                (sf_sign*.0059,sf_side*.0130,.1425),(sf_sign*.0045,sf_side*.0130,.1402)]
        tube('SF_Guard_PendantScroll',smooth_path(sf_pts,5),lambda t:.00056*(1-.30*t),'Silver','02_Guard',6)
        for sf_i in (1,2,4):
            sf_p=Vector(sf_pts[sf_i]);sf_q=sf_p+Vector((-sf_sign*.0016,sf_side*.0001,-.0017))
            tube('SF_Guard_PendantThorns',[sf_p,sf_p.lerp(sf_q,.55)+Vector((sf_sign*.0005,0,-.0004)),sf_q],lambda t:.0005*(1-.85*t),'Silver','02_Guard',6)
    # Raised swept crown follows the pointed collar visible above the reference
    # flower. Its lower arch leaves the flower's top petal fully exposed.
    sf_crown=[(-.0170,.1170),(-.0158,.1122),(-.0100,.1102),
              (-.0041,.1065),(0,.1038),(.0041,.1065),(.0100,.1102),
              (.0158,.1122),(.0170,.1170),(.0106,.1145),(.0058,.1124),
              (0,.1102),(-.0058,.1124),(-.0106,.1145)]
    extrude('SF_Guard_RaisedCrown',sf_crown,.0016,'Inlay','02_Guard',cy=sf_side*.0153)
    sf_guard_border('SF_Guard_CrownLip',sf_crown,sf_side,.01625,.00044,'Silver')
    # Compact branch lace peeks through the two narrow gaps beside the upper
    # petal and returns into the crown; no decorative line crosses the flower.
    for sf_sign in (-1,1):
        sf_crown_lace=[(sf_sign*.0015,sf_side*.0160,.1108),
                       (sf_sign*.0043,sf_side*.0163,.1123),
                       (sf_sign*.0088,sf_side*.0161,.1136),
                       (sf_sign*.0102,sf_side*.0163,.1179),
                       (sf_sign*.0085,sf_side*.0165,.1211),
                       (sf_sign*.0130,sf_side*.0161,.1233),
                       (sf_sign*.0143,sf_side*.0160,.1275)]
        tube('SF_Guard_CrownLace',smooth_path(sf_crown_lace,6),
             lambda t:.00046*(1-.24*t),'Inlay','02_Guard',7)
        for sf_j in (1,3,5):
            sf_p=Vector(sf_crown_lace[sf_j])
            sf_q=sf_p+Vector((sf_sign*.00135,sf_side*.0001,-.0020))
            sf_r=sf_q+Vector((-sf_sign*.00125,0,.00055))
            tube('SF_Guard_CrownThorns',[sf_p,sf_q,sf_r],
                 lambda t:.00040*(1-.78*t),'Silver','02_Guard',6)
        sf_fork=[(sf_sign*.0088,sf_side*.0161,.1136),
                 (sf_sign*.0061,sf_side*.0162,.1117),
                 (sf_sign*.0044,sf_side*.0163,.1138)]
        tube('SF_Guard_CrownFork',sf_fork,lambda t:.00034*(1-.56*t),
             'Silver','02_Guard',6)
    flower('SF_GuardFlower',(0,sf_side*.0170,.127),.0160,(0,sf_side,0),sf_side*math.pi/2,group='02_Guard',large=True)
