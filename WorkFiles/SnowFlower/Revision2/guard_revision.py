"""Compact traced guard: angular shoulders, paired leaves and thorned pendant."""

def sf_guard_plaque(name,outline,side,base,depth,material='BlackenedSteel',ridge=.0012):
    pts=[Vector((x,0,z)) for x,z in outline];cen=sum(pts,Vector())/len(pts);n=len(pts)
    vs=[(cen.x,side*(base+depth+ridge),cen.z)]
    vs.extend((p.x,side*(base+depth),p.z) for p in pts)
    vs.extend((p.x,side*base,p.z) for p in pts)
    fs=[]
    for i in range(n):
        j=(i+1)%n;fs.extend([(0,1+i,1+j),(1+i,n+1+i,n+1+j,1+j)])
    fs.append(tuple(n+1+i for i in reversed(range(n))))
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

sf_wing=[(.012,.118),(.038,.116),(.040,.111),(.055,.121),(.062,.131),(.060,.136),(.048,.149),(.034,.155),(.029,.145),(.019,.138)]
for sf_sign in (-1,1):
    sf_outline=[(sf_sign*x,z) for x,z in sf_wing]
    extrude('SF_Guard_Wings',sf_outline,.009,'Recess','02_Guard')
    for sf_side in (-1,1):
        sf_guard_border('SF_Guard_ShoulderEdge',sf_outline,sf_side,.0053,.0015)
        sf_inset=[(sf_sign*(.041+(x-.041)*.79),.131+(z-.131)*.73) for x,z in sf_wing]
        sf_guard_border('SF_Guard_SteppedRim',sf_inset,sf_side,.0060,.00075,'Inlay')
        # Interconnected curved lattice, recessed under the foreground petals.
        for sf_idx,sf_curve2 in enumerate([
            [(.027,.122),(.040,.123),(.050,.129),(.050,.137),(.043,.147),(.036,.148)],
            [(.043,.147),(.037,.139),(.036,.132),(.041,.129),(.047,.132),(.049,.138)],
            [(.050,.130),(.056,.133),(.053,.139),(.047,.146),(.039,.150)],
            [(.030,.129),(.034,.135),(.039,.136),(.044,.132),(.045,.127)]
        ]):
            sf_pts=[(sf_sign*x,sf_side*(.0068+.00035*(sf_idx%2)),z) for x,z in sf_curve2]
            tube('SF_Guard_ShoulderScrolls',smooth_path(sf_pts,7),.00062,'Inlay','02_Guard',7)
            for sf_j in (1,3):
                sf_p=Vector(sf_pts[sf_j]);sf_q=sf_p+Vector((sf_sign*.0018,sf_side*.0001,-.0034))
                tube('SF_Guard_ShoulderThorns',[sf_p,sf_p.lerp(sf_q,.5)+Vector((sf_sign*.001,0,0)),sf_q],lambda t:.00061*(1-.85*t),'Silver','02_Guard',6)

# Hand-shaped broad paired lateral petals, tapering inward at the flower.
sf_leaf=[(.006,.126),(.016,.123),(.028,.128),(.037,.139),(.043,.157),(.032,.151),(.026,.150),(.019,.146),(.013,.137)]
sf_small=[(.005,.123),(.011,.116),(.020,.112),(.029,.111),(.023,.117),(.015,.122)]
for sf_side in (-1,1):
    for sf_sign in (-1,1):
        sf_under=[(sf_sign*x,.129+(z-.129)*1.04+.0033) for x,z in sf_leaf]
        sf_guard_plaque('SF_Guard_UnderLeaves',sf_under,sf_side,.006,.0012,'Recess',.001)
        sf_guard_border('SF_Guard_UnderLeafRims',sf_under,sf_side,.0082,.0011)
        for sf_nm,sf_poly,sf_y in [('UpperLeaf',sf_small,.0090),('MainLeaf',sf_leaf,.0120)]:
            # A restrained subdivision of the contour softens leaf edges, not shoulders.
            sf_p=[Vector((sf_sign*x,0,z)) for x,z in sf_poly]
            sf_curve=[]
            for sf_i in range(len(sf_p)):
                sf_a,sf_b,sf_c,sf_d=[sf_p[j%len(sf_p)] for j in (sf_i-1,sf_i,sf_i+1,sf_i+2)]
                for sf_t in (0,.25,.5,.75):
                    sf_v=.5*((2*sf_b)+(-sf_a+sf_c)*sf_t+(2*sf_a-5*sf_b+4*sf_c-sf_d)*sf_t**2+(-sf_a+3*sf_b-3*sf_c+sf_d)*sf_t**3)
                    sf_curve.append((sf_v.x,sf_v.z))
            sf_guard_plaque('SF_Guard_'+sf_nm,sf_curve,sf_side,sf_y,.0014,'BlackenedSteel',.0022)
            sf_guard_border('SF_Guard_'+sf_nm+'Lip',sf_curve,sf_side,sf_y+.00155,.00080)
            # Inset lip follows outer border as a second cast rim.
            sf_cx=sf_sign*(.025 if sf_nm=='MainLeaf' else .016);sf_cz=.133 if sf_nm=='MainLeaf' else .116
            sf_inner=[(sf_cx+(x-sf_cx)*.86,sf_cz+(z-sf_cz)*.80) for x,z in sf_curve]
            sf_guard_border('SF_Guard_'+sf_nm+'Inset',sf_inner,sf_side,sf_y+.0020,.00038,'Inlay')
    sf_pendant=[(0,.133),(.010,.139),(.009,.150),(0,.170),(-.009,.150),(-.010,.139)]
    sf_guard_plaque('SF_Guard_CentralPendant',sf_pendant,sf_side,.006,.0012,'Recess',.001)
    sf_guard_border('SF_Guard_PendantOuterLip',sf_pendant,sf_side,.0085,.00125)
    sf_inner=[(0,.138),(.0055,.141),(.006,.148),(0,.163),(-.006,.148),(-.0055,.141)]
    sf_guard_border('SF_Guard_PendantPiercedFrame',sf_inner,sf_side,.0115,.00085)
    for sf_sign in (-1,1):
        sf_pts=[(0,sf_side*.011,.160),(sf_sign*.0025,sf_side*.0113,.153),(sf_sign*.0018,sf_side*.0114,.150),(sf_sign*.0040,sf_side*.0111,.147),(sf_sign*.0033,sf_side*.011,.143),(sf_sign*.0015,sf_side*.011,.141)]
        tube('SF_Guard_PendantScroll',smooth_path(sf_pts,5),lambda t:.00058*(1-.25*t),'Silver','02_Guard',6)
        for sf_i in (1,3,4):
            sf_p=Vector(sf_pts[sf_i]);sf_q=sf_p+Vector((-sf_sign*.002,sf_side*.0001,-.0019))
            tube('SF_Guard_PendantThorns',[sf_p,sf_p.lerp(sf_q,.55)+Vector((sf_sign*.0005,0,-.0004)),sf_q],lambda t:.0005*(1-.85*t),'Silver','02_Guard',6)
    flower('SF_GuardFlower',(0,sf_side*.0170,.127),.0160,(0,sf_side,0),sf_side*math.pi/2,group='02_Guard',large=True)
