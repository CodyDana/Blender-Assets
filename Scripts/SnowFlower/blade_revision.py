"""Reference-composed plum branches with varied forks and sparse distal ornament."""
for sf_side in (-1,1):
    sf_name='SF_BladeRelief_Front' if sf_side==-1 else 'SF_BladeRelief_Back'
    # Irregularly spaced bends follow the reference's changing branch rhythm.
    # Coordinates are fractions along the exposed blade and across its width.
    sf_knots=[(0,-.11),(.016,-.02),(.034,.20),(.049,.17),(.062,-.03),
        (.078,-.17),(.092,-.14),(.101,-.22),(.118,-.18),(.138,.04),
        (.154,.15),(.174,.12),(.198,-.11),(.218,-.19),(.235,-.07),
        (.251,-.02),(.270,.13),(.285,.20),(.310,.13),(.333,.06),
        (.363,-.13),(.393,-.15),(.417,-.04),(.439,.09),(.462,.14),
        (.490,.12),(.521,-.05),(.552,-.16),(.582,-.13),(.606,.06),
        (.622,.13),(.641,.10),(.665,-.07),(.693,-.17),(.730,-.15),
        (.762,-.07),(.795,.12),(.819,.15),(.845,.02),(.874,-.08),(.930,.10)]
    sf_knots=[(t,u*1.5) for t,u in sf_knots]

    def sf_point(t,u,offset=0):
        z=.166+.905*t;c,w,h=blade_shape(z)
        u=u if sf_side==-1 else -u*.92+.023*math.sin(t*27)
        x=c+u*w
        return Vector((x,surface(x,z,sf_side)+sf_side*offset,z))

    sf_path=[sf_point(t,u) for t,u in sf_knots]
    # Woody nodes are swellings in the continuous trunk, not oval applied pads.
    sf_radii=[]
    for sf_t,sf_u in sf_knots:
        sf_swell=sum(.32*math.exp(-((sf_t-c)/.009)**2) for c in (.092,.198,.285,.417,.622,.795))
        sf_radii.append((.00195*(1-sf_t)**.65+.00015)*(1+.11*math.sin(sf_t*63)+sf_swell))
    sf_path.insert(0,Vector((.006,surface(.006,.144,sf_side),.144)));sf_radii.insert(0,.0022)
    relief_branch(sf_name+'_Trunk',sf_path,sf_radii,sf_side)
    sf_samples=smooth_path(sf_path,24)

    def sf_main_at(t):
        z=.166+.905*t
        j=next((j for j in range(len(sf_samples)-1) if sf_samples[j].z<=z<=sf_samples[j+1].z),len(sf_samples)-2)
        a,b=sf_samples[j],sf_samples[j+1]
        return a.lerp(b,max(0,min(1,(z-a.z)/max(1e-8,b.z-a.z))))

    def sf_flower_point(t,u,radius,base=.00048):
        p=sf_point(t,u,base)
        # Petals that overlap the trunk must sit above its raised crown.
        # Their stalk follows this same anchor, providing a connected seat.
        if abs(p.x-sf_main_at(t).x)<radius+.0020:
            p=sf_point(t,u,max(base,.00245*(1-t*.65)))
        return p

    # Individually placed clusters: solitary blooms, overlapping pairs, and
    # irregular groups retain the two main decorated zones of the reference.
    # Each entry is main(t,u,radius,phase), followed by explicit satellites.
    sf_clusters=[
        ((.008,.17,.0064,.15),[(.015,.03,.0032,1.1)]),
        ((.074,-.15,.0067,.87),[(.064,-.27,.0032,.2),(.086,-.08,.0027,2.1)]),
        ((.115,.19,.0063,1.5),[]),
        ((.149,-.18,.0070,2.4),[(.150,-.02,.0041,1.0),(.158,-.21,.0035,.4)]),
        ((.182,.12,.0052,.3),[(.179,.28,.0030,1.8)]),
        ((.267,.14,.0068,2.0),[(.256,.25,.0038,.7),(.276,.24,.0042,2.8)]),
        ((.294,-.13,.0057,1.1),[]),
        ((.616,-.12,.0063,.4),[(.615,.06,.0042,1.5)]),
        ((.650,.15,.0059,2.7),[(.643,.25,.0031,.1),(.659,.04,.0033,1.9)]),
    ]
    for sf_i,(sf_main,sf_satellites) in enumerate(sf_clusters):
        sf_t,sf_u,sf_r,sf_phase=sf_main
        sf_base_t=max(0,sf_t-(.011,.021,.015,.028)[sf_i%4])
        sf_base=sf_main_at(sf_base_t)
        sf_target=sf_flower_point(sf_t,sf_u,sf_r)
        sf_mid=sf_base.lerp(sf_target,.52)
        sf_mid.x+=(-1 if sf_i%2 else 1)*.0011
        sf_mid.z-=.0015 if sf_i%3 else .0030
        sf_shoulder=sf_base.lerp(sf_mid,.28)
        relief_branch(sf_name+'_Twigs',[sf_base,sf_shoulder,sf_mid,sf_target],
                      [.00120,.00108,.00063,.00029],sf_side)
        sf_normal=Vector((.045*math.sin(sf_i*2.1),sf_side,.055*math.cos(sf_i*1.7))).normalized()
        flower(sf_name,sf_target,sf_r,sf_normal,sf_phase+sf_side*.15)
        for sf_j,(sf_t2,sf_u2,sf_r2,sf_phase2) in enumerate(sf_satellites):
            sf_tp=sf_flower_point(sf_t2,sf_u2,sf_r2,.00044+sf_j*.00008)
            sf_start=sf_target.lerp(sf_mid,.52)
            sf_turn=sf_start.lerp(sf_tp,.55)+Vector((.0006*(-1 if sf_j%2 else 1),0,-.0012))
            relief_branch(sf_name+'_FlowerStalk',[sf_start,sf_turn,sf_tp],
                          [.00054,.00040,.00022],sf_side,woody=False)
            sf_n=Vector((.075*math.sin(sf_i+sf_j),sf_side,.055*math.cos(sf_i-sf_j))).normalized()
            flower(sf_name,sf_tp,sf_r2,sf_n,sf_phase2)

    # Short bare forks end in small closed buds; distal ornament stays sparse.
    for sf_i,sf_t in enumerate((.040,.103,.126,.212,.285,.351,.449,.533,.604,.687,.789,.863)):
        sf_p=sf_main_at(sf_t)
        sf_z=.166+.905*sf_t;sf_c,sf_w,sf_h=blade_shape(sf_z)
        sf_u=(sf_p.x-sf_c)/sf_w
        if sf_side==1:sf_u=-(sf_u-.023*math.sin(sf_t*27))/.92
        sf_sign=1 if sf_i%2 else -1
        sf_q=sf_point(sf_t+(.009 if sf_i%3 else .014),max(-.31,min(.31,sf_u+sf_sign*.14)),.00012)
        sf_bend=sf_p.lerp(sf_q,.60)+Vector((sf_sign*.0007,0,-.0019))
        relief_branch(sf_name+'_BareFork',[sf_p,sf_bend,sf_q],
                      [.00072*(1-sf_t*.6),.00042,.00017],sf_side,woody=False)
        sf_budr=.00076 if sf_t<.7 else .00046
        sf_dir=(sf_q-sf_bend).normalized();sf_lat=Vector((sf_dir.z,0,-sf_dir.x)).normalized()
        ellipsoid(sf_name+'_Buds',sf_q+sf_dir*sf_budr*.4,
                  sf_lat*sf_budr,Vector((0,sf_budr*.62,0)),sf_dir*sf_budr*1.45,
                  'Silver','03_FloralRelief',10,5)
