"""Reference-composed plum branches with sparse distal ornament."""
for sf_side in (-1,1):
    sf_name='SF_BladeRelief_Front' if sf_side==-1 else 'SF_BladeRelief_Back'
    # x values are fractions of the dark blade width, t runs from guard to tip.
    sf_knots=[(.0,-.11),(.025,-.17),(.058,-.08),(.086,.12),(.121,.17),(.157,.07),(.191,-.12),(.228,-.16),(.276,-.04),(.311,.14),(.361,.17),(.407,.10),(.453,-.07),(.500,-.16),(.551,-.13),(.602,.07),(.643,.15),(.680,.08),(.724,-.11),(.777,-.17),(.826,-.07),(.874,.06),(.930,.10)]
    sf_knots=[(t,u*1.5) for t,u in sf_knots]
    def sf_point(t,u,offset=0):
        z=.166+.905*t;c,w,h=blade_shape(z)
        # back view follows the same cluster hierarchy with shifted branch bends.
        u=u if sf_side==-1 else -u*.92+.023*math.sin(t*27)
        x=c+u*w
        return Vector((x,surface(x,z,sf_side)+sf_side*offset,z))
    sf_path=[sf_point(t,u) for t,u in sf_knots]
    sf_radii=[(.00195*(1-t)**.65+.00015)*(1+.16*math.sin(t*63)) for t,u in sf_knots]
    sf_path.insert(0,Vector((.006,surface(.006,.144,sf_side),.144)));sf_radii.insert(0,.0022)
    relief_branch(sf_name+'_Trunk',sf_path,sf_radii,sf_side)
    # Short broken bark ridges and knuckles give the raised trunk a woody character.
    for sf_i in (2,4,6,9,12,15,18):
        sf_t,sf_u=sf_knots[sf_i];sf_p=sf_point(sf_t,sf_u,.0008)
        sf_rr=sf_radii[sf_i]
        sf_p.x+=sf_rr*.35*(-1 if sf_i%2 else 1)
        ellipsoid(sf_name+'_Knuckles',sf_p,(sf_rr*1.38,0,0),(0,sf_rr*.52,0),(sf_rr*.42,0,sf_rr*2.05),'BranchSteel','03_FloralRelief',12,6)
        sf_bark=[]
        for sf_j in range(9):
            sf_a=-1.1+sf_j/8*2.2
            sf_bark.append(sf_p+Vector((math.sin(sf_a)*sf_rr*.95,sf_side*sf_rr*.45,math.cos(sf_a)*sf_rr*1.5)))
        tube(sf_name+'_KnotCreases',sf_bark,sf_rr*.045,'Recess','03_FloralRelief',4)
    # The sheet groups blossoms densely near the hilt and again at ~two thirds.
    sf_clusters=[(.008,.17,.0064),(.074,-.13,.0067),(.115,.19,.0063),(.149,-.18,.0070),(.182,.12,.0052),(.267,.14,.0068),(.294,-.13,.0057),(.616,-.12,.0063),(.650,.15,.0059)]
    for sf_i,(sf_t,sf_u,sf_r) in enumerate(sf_clusters):
        sf_base_t=max(0,sf_t-.020)
        sf_seg=next((i for i in range(len(sf_knots)-1) if sf_knots[i][0]<=sf_base_t<=sf_knots[i+1][0]),len(sf_knots)-2)
        sf_a,sf_b=sf_knots[sf_seg],sf_knots[sf_seg+1];sf_factor=(sf_base_t-sf_a[0])/(sf_b[0]-sf_a[0])
        sf_base=sf_point(sf_base_t,sf_a[1]*(1-sf_factor)+sf_b[1]*sf_factor)
        sf_target=sf_point(sf_t,sf_u,.00035)
        sf_mid=sf_base.lerp(sf_target,.55);sf_mid.z-=.0017
        relief_branch(sf_name+'_Twigs',[sf_base,sf_mid,sf_target],[.00090,.00069,.00031],sf_side)
        flower(sf_name,sf_target,sf_r,(0,sf_side,0),sf_i*.77+sf_side*.25)
        for sf_j,(sf_dt,sf_du,sf_scale) in enumerate([(-.006,-.12,.58),(.008,.105,.43)] if sf_i in (1,2,3,5,7,8) else [(.008,-.11,.48)]):
            sf_u2=max(-.235,min(.235,sf_u+sf_du));sf_tp=sf_point(sf_t+sf_dt,sf_u2,.00029)
            sf_start=sf_target.lerp(sf_mid,.5)
            relief_branch(sf_name+'_FlowerStalk',[sf_start,sf_tp],[.00050,.00024],sf_side,woody=False)
            flower(sf_name,sf_tp,sf_r*sf_scale,(0,sf_side,0),sf_i+sf_j+.4)
    # Bare short forks and attached buds, mainly in quiet blade regions.
    for sf_i in (1,3,5,8,10,13,16,17,19,20):
        sf_t,sf_u=sf_knots[sf_i];sf_p=sf_point(sf_t,sf_u)
        sf_sign=1 if sf_i%2 else -1;sf_q=sf_point(sf_t+.013,max(-.26,min(.26,sf_u+sf_sign*.10)),.00012)
        relief_branch(sf_name+'_BareFork',[sf_p,sf_p.lerp(sf_q,.6)+Vector((0,0,-.001)),sf_q],[.0007*(1-sf_t*.6),.00042,.00016],sf_side,woody=False)
        sf_budr=.00075 if sf_t<.7 else .00045
        ellipsoid(sf_name+'_Buds',sf_q,(sf_budr,0,0),(0,sf_budr*.6,0),(0,0,sf_budr*1.2),'Silver','03_FloralRelief',10,5)
